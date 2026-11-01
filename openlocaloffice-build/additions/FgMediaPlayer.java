package com.openlocal.office.core;

import android.app.Activity;
import android.net.Uri;
import android.content.pm.ActivityInfo;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.widget.LinearLayout;
import android.os.StatFs;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.TextView;
import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.exoplayer.source.ProgressiveMediaSource;
import androidx.media3.ui.PlayerView;
import java.io.*;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Android media playback for SAF content, including provider streams.
 * Never blocks the UI on a cloud download. ExoPlayer streams when possible;
 * if a provider cannot seek, a single cached copy is tried automatically.
 */
@androidx.media3.common.util.UnstableApi
public final class FgMediaPlayer implements AutoCloseable {
    public interface MediaNavigator {
        void navigate(int direction,boolean random);
    }
    private final MediaNavigator mediaNavigator;
    private final Activity activity;
    private final FrameLayout root;
    private final TextView status;
    private final PlayerView display;
    private final int previousOrientation;
    private final int previousSystemUi;
    private final boolean wasFullscreen;
    private final boolean wasKeepScreenOn;
    private final ExoPlayer player;
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private volatile boolean closed;
    private volatile boolean fallbackStarted;
    private volatile int session=1;
    private volatile FgGrowingMediaDataSource.Progress growing;
    private Uri original;
    private String filename;
    private boolean video;
    private volatile File transientMediaFile;
    private final boolean teraboxDirect;
    private final Runnable onExit;
    // Persistent player mode survives switching to the next video.
    // 0 = Play Next, 1 = Replay, 2 = Shuffle without immediate repetition.
    private static volatile int playbackMode=0;
    private boolean endHandled=false;

    public FgMediaPlayer(Activity activity,Uri original,String filename,
                         boolean video,Runnable onExit,MediaNavigator mediaNavigator){
        this.activity=activity;this.original=original;this.filename=filename;
        this.video=video;this.onExit=onExit;
        this.mediaNavigator=mediaNavigator;
        teraboxDirect=FgTeraboxDocumentsProvider.AUTHORITY.equals(original.getAuthority());
        previousOrientation=activity.getRequestedOrientation();
        previousSystemUi=activity.getWindow().getDecorView().getSystemUiVisibility();
        int flags=activity.getWindow().getAttributes().flags;
        wasFullscreen=(flags&android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN)!=0;
        wasKeepScreenOn=(flags&android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)!=0;
        root=new FrameLayout(activity);
        root.setBackgroundColor(0xff090c13);
        display=new PlayerView(activity);
        display.setUseController(true);
        if(video){
            display.setControllerShowTimeoutMs(2600);
            // Media3's built-in skip/seek neighbours collide visually with
            // Rounder's own previous/next-folder-video controls.
            // Keep exactly one playlist pair, plus Media3's central play/pause.
            display.setShowPreviousButton(false);
            display.setShowNextButton(false);
            display.setShowRewindButton(false);
            display.setShowFastForwardButton(false);
        }
        FrameLayout.LayoutParams videoLayout=new FrameLayout.LayoutParams(-1,-1);
        videoLayout.gravity=Gravity.CENTER;
        root.addView(display,videoLayout);
        player=new ExoPlayer.Builder(activity).build();
        display.setPlayer(player);
        if(video){
            // Some Media3 Controller layouts retain the legacy seek buttons
            // even when PlayerView flags are false. Hide only the competing
            // symbols, not the seek bar or playback/pause control.
            for(int id:new int[]{
                androidx.media3.ui.R.id.exo_prev,
                androidx.media3.ui.R.id.exo_next,
                androidx.media3.ui.R.id.exo_rew,
                androidx.media3.ui.R.id.exo_ffwd
            }){
                View duplicate=display.findViewById(id);
                if(duplicate!=null)duplicate.setVisibility(View.GONE);
            }
        }
        TextView title=new TextView(activity);
        title.setText((video?"Video Â· ":"Audio Â· ")+filename);
        title.setTextColor(0xffffffff);
        title.setBackgroundColor(0xcc152039);
        title.setPadding(20,16,150,16);
        title.setTextSize(14);
        if(!video)root.addView(title,new FrameLayout.LayoutParams(-1,-2,Gravity.TOP));
        Button back=new Button(activity);
        back.setText("Back");
        back.setOnClickListener(v->onExit.run());
        if(!video)root.addView(back,new FrameLayout.LayoutParams(-2,-2,Gravity.TOP|Gravity.RIGHT));
        else {
            // Edge taps capture only the middle of the image, preserving
            // Media3's seek bar and central playback controls.
            final LinearLayout gestureRow=new LinearLayout(activity);
            gestureRow.setOrientation(LinearLayout.HORIZONTAL);
            for(int side=-1;side<=1;side++){
                View zone=new View(activity);
                gestureRow.addView(zone,new LinearLayout.LayoutParams(0,-1,1f));
                if(side==0)continue;
                final int direction=side;
                GestureDetector detector=new GestureDetector(activity,
                    new GestureDetector.SimpleOnGestureListener(){
                        @Override public boolean onDown(MotionEvent event){return true;}
                        @Override public boolean onSingleTapConfirmed(MotionEvent event){
                            if(display.isControllerFullyVisible())display.hideController();
                            else display.showController();
                            return true;
                        }
                        @Override public boolean onDoubleTap(MotionEvent event){
                            if(!closed && player.isCommandAvailable(Player.COMMAND_SEEK_IN_CURRENT_MEDIA_ITEM)){
                                long position=player.getCurrentPosition()+direction*10000L;
                                long duration=player.getDuration();
                                position=Math.max(0L,position);
                                if(duration>0)position=Math.min(position,duration);
                                player.seekTo(position);
                                Log.i("FG_MEDIA", direction<0?"DOUBLE_TAP_BACK_10S":"DOUBLE_TAP_FORWARD_10S");
                            }
                            return true;
                        }
                    });
                zone.setOnTouchListener((v,event)->detector.onTouchEvent(event));
            }
            root.addView(gestureRow,new FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));
            root.addOnLayoutChangeListener((v,left,top,right,bottom,ol,ot,or_,ob)->{
                FrameLayout.LayoutParams params=(FrameLayout.LayoutParams)gestureRow.getLayoutParams();
                int desired=Math.max(1,Math.round((bottom-top)*0.72f));
                if(params.height!=desired){
                    params.height=desired;params.gravity=Gravity.CENTER;
                    gestureRow.setLayoutParams(params);
                }
            });
            // One unambiguous folder-navigation group, away from Media3's
            // center play/pause and bottom seek-bar controls.
            final LinearLayout controls=new LinearLayout(activity);
            controls.setOrientation(LinearLayout.HORIZONTAL);
            controls.setGravity(Gravity.CENTER_VERTICAL);
            final Button prev=new Button(activity);
            final Button next=new Button(activity);
            prev.setText("◀ Prev");
            next.setText("Next ▶");
            prev.setContentDescription("Previous video in this folder");
            next.setContentDescription("Next video in this folder");
            prev.setOnClickListener(v->{if(mediaNavigator!=null)mediaNavigator.navigate(-1,false);});
            next.setOnClickListener(v->{if(mediaNavigator!=null)mediaNavigator.navigate(1,false);});
            controls.addView(prev,new LinearLayout.LayoutParams(0,-2,1f));
            controls.addView(next,new LinearLayout.LayoutParams(0,-2,1f));
            final LinearLayout modes=new LinearLayout(activity);
            modes.setGravity(Gravity.CENTER);
            final String[] modeNames={"Play next","Replay","Shuffle"};
            final Button[] modeButtons=new Button[3];
            for(int i=0;i<3;i++){
                final int selectedMode=i;
                Button button=new Button(activity);
                button.setAllCaps(false);
                button.setText(modeNames[i]);
                button.setTextSize(11);
                button.setMinHeight(0);
                button.setContentDescription("Playback mode: "+modeNames[i]);
                modes.addView(button,new LinearLayout.LayoutParams(0,-2,1f));
                modeButtons[i]=button;
                button.setOnClickListener(v->{
                    playbackMode=selectedMode;
                    refreshPlaybackMode(modeButtons);
                });
            }
            refreshPlaybackMode(modeButtons);
            final LinearLayout panel=new LinearLayout(activity);
            panel.setOrientation(LinearLayout.VERTICAL);
            panel.setPadding(8,0,8,0);
            panel.setBackgroundColor(0xbb0c1424);
            panel.addView(controls,new LinearLayout.LayoutParams(-1,-2));
            panel.addView(modes,new LinearLayout.LayoutParams(-1,-2));
            final int bottom=(int)(84*activity.getResources().getDisplayMetrics().density);
            FrameLayout.LayoutParams panelParams=new FrameLayout.LayoutParams(
                -1,-2,Gravity.BOTTOM);
            panelParams.bottomMargin=bottom;
            root.addView(panel,panelParams);
            display.setControllerVisibilityListener(
                (PlayerView.ControllerVisibilityListener) visibility->{
                    panel.setVisibility(visibility==View.VISIBLE?View.VISIBLE:View.GONE);
                });
            enterVideoFullscreen();
        }
        status=new TextView(activity);
        status.setTextColor(0xffcbd9ed);
        status.setTextSize(13);
        status.setBackgroundColor(0xbb101827);
        status.setPadding(14,12,14,12);
        root.addView(status,new FrameLayout.LayoutParams(
            video?-2:-1,-2,video?(Gravity.BOTTOM|Gravity.CENTER_HORIZONTAL):Gravity.BOTTOM));
        player.addListener(new Player.Listener(){
            @Override public void onPlaybackStateChanged(int state){
                if(closed)return;
                if(state==Player.STATE_READY){
                    endHandled=false;showMessage("");
                    Log.i("FG_MEDIA","MEDIA_READY "+filename+
                        " duration_ms="+player.getDuration());
                }else if(state==Player.STATE_BUFFERING)
                    showMessage("Buffering video…");
                else if(state==Player.STATE_ENDED){
                    if(endHandled)return;
                    endHandled=true;
                    if(playbackMode==1){
                        player.seekTo(0);player.play();
                        showMessage("");
                    }else if(mediaNavigator!=null){
                        mediaNavigator.navigate(playbackMode==2?0:1,playbackMode==2);
                    }else showMessage("Playback finished");
                }
            }
            @Override public void onRenderedFirstFrame(){
                Log.i("FG_MEDIA","VIDEO_FIRST_FRAME "+filename);
            }
            @Override public void onPlayerError(PlaybackException error){
                Log.e("FG_MEDIA","PLAYBACK_ERROR code="+error.getErrorCodeName(),error);
                if(teraboxDirect){
                    // A cloud file is a seekable data source. Falling back to
                    // copyThenPlay() would silently download the entire video.
                    showMessage("TeraBox playback unavailable: "+error.getErrorCodeName()+
                        " · tap Back to retry");
                }else if(!fallbackStarted){
                    fallbackStarted=true;copyThenPlay();
                }else showMessage("Unable to decode or play this file: "+error.getMessage());
            }
        });
        // TeraBox supports seekable native ranges. Other selected Android
        // documents use their granted file URI; progressive fallback is
        // activated only if the media decoder reports an actual failure.
        if(teraboxDirect)playTeraboxRanges();
        else play(original);
    }
    private void playTeraboxRanges(){
        try{
            Log.i("FG_MEDIA","TERABOX_DIRECT_RANGE_PLAY");
            androidx.media3.datasource.DataSource.Factory factory=
                ()->new FgTeraboxMediaDataSource(activity,original);
            player.setMediaSource(new ProgressiveMediaSource.Factory(factory)
                .createMediaSource(MediaItem.fromUri(original)));
            player.prepare();player.play();
        }catch(Exception error){
            Log.e("FG_MEDIA","TERABOX_RANGE_PREPARE_FAILED",error);
            showMessage("Unable to start cloud video: "+error.getMessage());
        }
    }
    private static void refreshPlaybackMode(Button[] buttons){
        for(int i=0;i<buttons.length;i++){
            boolean selected=i==playbackMode;
            buttons[i].setTextColor(android.graphics.Color.WHITE);
            buttons[i].setBackgroundTintList(
                android.content.res.ColorStateList.valueOf(
                    selected?0xff456ae8:0xff273449));
            buttons[i].setAlpha(selected?1f:0.78f);
            buttons[i].setSelected(selected);
        }
    }
    public View getView(){return root;}
    private void enterVideoFullscreen(){
        activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        activity.getWindow().addFlags(
            android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN |
            android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        activity.getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN |
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
    }
    private void leaveVideoFullscreen(){
        activity.getWindow().getDecorView().setSystemUiVisibility(previousSystemUi);
        if(!wasFullscreen)activity.getWindow().clearFlags(
            android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN);
        if(!wasKeepScreenOn)activity.getWindow().clearFlags(
            android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        activity.setRequestedOrientation(previousOrientation);
    }
    private void showMessage(String message){
        activity.runOnUiThread(()->{
            if(closed)return;
            // Download progress must not cover the video seek bar or remain
            // visible throughout normal progressive playback.
            String shown=video && player.getPlaybackState()==Player.STATE_READY &&
                message.startsWith("Streaming ")?"":message;
            status.setText(shown);
            status.setVisibility(shown.isEmpty()?View.GONE:View.VISIBLE);
        });
    }
    private void play(Uri uri){
        if(closed)return;
        try{
            Log.i("FG_MEDIA","PLAY_START "+uri.getScheme()+" "+uri.getAuthority());
            player.setMediaItem(MediaItem.fromUri(uri));
            player.prepare();
            player.play();
        }catch(Exception e){
            Log.e("FG_MEDIA","MEDIA_PREPARE_FAILED",e);
            if(!fallbackStarted){fallbackStarted=true;copyThenPlay();}
            else showMessage("Playback failed: "+e.getMessage());
        }
    }
    private static String digest(Uri uri){
        try{
            byte[] bytes=MessageDigest.getInstance("SHA-256")
                .digest(uri.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder text=new StringBuilder();
            for(int i=0;i<16;i++)text.append(String.format(Locale.ROOT,"%02x",bytes[i]&255));
            return text.toString();
        }catch(Exception e){throw new IllegalStateException(e);}
    }
    /** MP4s with a fast-start index can begin once the first bytes arrive.
     * Do not wait for an entire multi-GB remote movie. An MP4 with its
     * moov index at the end still requires seekable provider or later bytes.
     */
    private void copyThenPlay(){
        final int version=session;
        showMessage("Connecting to video streamâ€¦");
        io.execute(()->{
            FgGrowingMediaDataSource.Progress progress=null;
            try{
                File cacheDir=new File(activity.getExternalCacheDir()!=null?
                    activity.getExternalCacheDir():activity.getCacheDir(),"fg-media-session-v3");
                if(!cacheDir.exists()&&!cacheDir.mkdirs())
                    throw new IOException("Media cache directory is not available");
                String low=filename.toLowerCase(Locale.ROOT);
                String extension=".mp4";
                for(String suffix:new String[]{".webm",".mkv",".mov",".m4a",
                    ".mp3",".flac",".wav",".ogg",".opus"}){
                    if(low.endsWith(suffix)){extension=suffix;break;}
                }
                // Player scratch is session-only. Never reuse a completed
                // remote movie as a cache in subsequent sessions.
                File ready=new File(cacheDir,"session-"+
                    java.util.UUID.randomUUID()+extension);
                transientMediaFile=ready;
                if(!ready.createNewFile())throw new IOException("Cannot create session media stream");
                progress=new FgGrowingMediaDataSource.Progress(ready);
                growing=progress;
                final FgGrowingMediaDataSource.Progress state=progress;
                // Start ExoPlayer immediately. Its decoder will block only
                // when it asks for bytes not yet received from the provider.
                activity.runOnUiThread(()->{
                    if(closed||version!=session)return;
                    try{
                        androidx.media3.datasource.DataSource.Factory factory=
                            ()->new FgGrowingMediaDataSource(state);
                        player.setMediaSource(new ProgressiveMediaSource.Factory(factory)
                            .createMediaSource(MediaItem.fromUri(Uri.fromFile(ready))));
                        player.prepare();player.play();
                        Log.i("FG_MEDIA","PROGRESSIVE_PLAYBACK_START "+filename);
                    }catch(Exception e){
                        Log.e("FG_MEDIA","PROGRESSIVE_PREPARE_FAILED",e);
                        showMessage("Video cannot start: "+e.getMessage());
                    }
                });
                long written=0,reported=0;
                try(InputStream in=activity.getContentResolver().openInputStream(original);
                    FileOutputStream out=new FileOutputStream(ready)){
                    if(in==null)throw new IOException("Media provider returned no stream");
                    byte[] buffer=new byte[128*1024];
                    int n;
                    while((n=in.read(buffer))!=-1){
                        if(closed||version!=session)
                            throw new IOException("Playback cancelled");
                        out.write(buffer,0,n);
                        // Flush each chunk before publishing its length to
                        // readers that may be waiting at that offset.
                        out.flush();
                        written+=n;
                        state.available=written;
                        state.wake();
                        if(written-reported>=2L*1024*1024){
                            reported=written;
                            final long copied=written;
                            Log.i("FG_MEDIA","STREAM_BYTES_READY "+copied);
                            showMessage("Streaming "+copied/1048576+" MB receivedâ€¦");
                            StatFs stat=new StatFs(cacheDir.getAbsolutePath());
                            if(stat.getAvailableBytes()<64L*1024*1024)
                                throw new IOException("Not enough space to cache video");
                        }
                    }
                }
                if(written==0)throw new IOException("Video file is empty");
                state.finished=true;state.wake();
                Log.i("FG_MEDIA","STREAM_DOWNLOAD_COMPLETE bytes="+written);
            }catch(Exception e){
                Log.e("FG_MEDIA","VIDEO_STREAM_FAILED",e);
                if(progress!=null){
                    progress.failure=e instanceof IOException?(IOException)e:new IOException(e);
                    progress.finished=true;progress.wake();
                }
                if(!closed&&version==session)
                    showMessage("Video stream failed: "+e.getMessage());
            }
        });
    }
    @Override public void close(){
        closed=true;session++;
        if(growing!=null){growing.cancelled=true;growing.wake();}
        player.stop();player.release();
        io.shutdownNow();
        File scratch=transientMediaFile;
        transientMediaFile=null;
        if(scratch!=null && scratch.exists())scratch.delete();
        if(video)leaveVideoFullscreen();
    }
}