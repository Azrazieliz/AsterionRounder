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
    private final Runnable onExit;

    public FgMediaPlayer(Activity activity,Uri original,String filename,
                         boolean video,Runnable onExit){
        this.activity=activity;this.original=original;this.filename=filename;
        this.video=video;this.onExit=onExit;
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
            display.setShowRewindButton(false);
            display.setShowFastForwardButton(false);
        }
        FrameLayout.LayoutParams videoLayout=new FrameLayout.LayoutParams(-1,-1);
        videoLayout.gravity=Gravity.CENTER;
        root.addView(display,videoLayout);
        player=new ExoPlayer.Builder(activity).build();
        display.setPlayer(player);
        TextView title=new TextView(activity);
        title.setText((video?"Video · ":"Audio · ")+filename);
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
            enterVideoFullscreen();
        }
        status=new TextView(activity);
        status.setTextColor(0xffcbd9ed);
        status.setTextSize(13);
        status.setBackgroundColor(0xbb101827);
        status.setPadding(14,12,14,12);
        root.addView(status,new FrameLayout.LayoutParams(
            video?-2:-1,-2,video?(Gravity.TOP|Gravity.CENTER_HORIZONTAL):Gravity.BOTTOM));
        player.addListener(new Player.Listener(){
            @Override public void onPlaybackStateChanged(int state){
                if(closed)return;
                if(state==Player.STATE_READY){
                    showMessage("");
                    Log.i("FG_MEDIA","MEDIA_READY "+filename+
                        " duration_ms="+player.getDuration());
                }else if(state==Player.STATE_BUFFERING)
                    showMessage("Buffering from "+original.getAuthority()+"…");
                else if(state==Player.STATE_ENDED)showMessage("Playback finished");
            }
            @Override public void onRenderedFirstFrame(){
                Log.i("FG_MEDIA","VIDEO_FIRST_FRAME "+filename);
            }
            @Override public void onPlayerError(PlaybackException error){
                Log.e("FG_MEDIA","PLAYBACK_ERROR code="+error.getErrorCodeName(),error);
                if(!fallbackStarted){
                    fallbackStarted=true;
                    copyThenPlay();
                }else showMessage("Unable to decode or play this file: "+error.getMessage());
            }
        });
        // Round Sync's remote SAF documents generally expose a sequential
        // pipe; its random seeks can hang while opening large MP4s. Start
        // one progressive local stream immediately for that provider rather
        // than waiting for the seek attempt to time out.
        if("de.felixnuesse.extract.vcp".equals(original.getAuthority())){
            fallbackStarted=true;
            Log.i("FG_MEDIA","REMOTE_PIPE_PROGRESSIVE "+filename);
            copyThenPlay();
        }else play(original);
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
        showMessage("Connecting to video stream…");
        io.execute(()->{
            FgGrowingMediaDataSource.Progress progress=null;
            try{
                File cacheDir=new File(activity.getExternalCacheDir()!=null?
                    activity.getExternalCacheDir():activity.getCacheDir(),"fg-media-v2");
                if(!cacheDir.exists()&&!cacheDir.mkdirs())
                    throw new IOException("Media cache directory is not available");
                String low=filename.toLowerCase(Locale.ROOT);
                String extension=".mp4";
                for(String suffix:new String[]{".webm",".mkv",".mov",".m4a",
                    ".mp3",".flac",".wav",".ogg",".opus"}){
                    if(low.endsWith(suffix)){extension=suffix;break;}
                }
                File ready=new File(cacheDir,digest(original)+extension);
                File complete=new File(cacheDir,digest(original)+".complete");
                if(ready.isFile()&&ready.length()>0&&complete.isFile()){
                    if(!closed&&version==session)
                        activity.runOnUiThread(()->play(Uri.fromFile(ready)));
                    return;
                }
                // Only this file's incomplete cache is cleared; no app data
                // or other downloaded media are deleted.
                if(complete.exists())complete.delete();
                if(ready.exists()&&!ready.delete())
                    throw new IOException("Cannot reset partial media cache");
                if(!ready.createNewFile())throw new IOException("Cannot create media cache");
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
                            showMessage("Streaming "+copied/1048576+" MB received…");
                            StatFs stat=new StatFs(cacheDir.getAbsolutePath());
                            if(stat.getAvailableBytes()<64L*1024*1024)
                                throw new IOException("Not enough space to cache video");
                        }
                    }
                }
                if(written==0)throw new IOException("Video file is empty");
                state.finished=true;state.wake();
                try(FileOutputStream marker=new FileOutputStream(complete)){
                    marker.write(Long.toString(written).getBytes(
                        java.nio.charset.StandardCharsets.US_ASCII));
                }
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
        if(video)leaveVideoFullscreen();
    }
}