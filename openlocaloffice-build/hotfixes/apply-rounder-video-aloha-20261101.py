#!/usr/bin/env python3
"""Replace obstructive video bars with one Aloha-reference-style, functional native overlay."""
from pathlib import Path
path=Path("app/src/main/java/com/openlocal/office/core/FgMediaPlayer.java")
s=path.read_text(encoding="utf-8")
s=s.replace('''        if(video){
            display.setControllerShowTimeoutMs(2600);''','''        if(video){
            display.setUseController(false);
            display.setControllerShowTimeoutMs(2600);''',1)
start=s.index("            // Edge taps capture only the middle of the image")
end=s.index("            enterVideoFullscreen();",start)
replacement=r'''            // Aloha-style fullscreen video chrome: one narrow title/action row,
            // central transport, native seek timeline and compact mode bar.
            // No duplicate Media3 transport or oversized PREV/NEXT panels.
            final float dp=activity.getResources().getDisplayMetrics().density;
            final android.graphics.drawable.GradientDrawable pill=
                new android.graphics.drawable.GradientDrawable();
            pill.setColor(0xe5191c24);pill.setCornerRadius(24*dp);
            final LinearLayout heading=new LinearLayout(activity);
            heading.setGravity(Gravity.CENTER_VERTICAL);
            heading.setPadding((int)(12*dp),0,(int)(10*dp),0);
            heading.setBackgroundColor(0xc40d0d12);
            final Button close=new Button(activity);
            close.setText("×");close.setTextColor(-1);close.setTextSize(24);
            close.setAllCaps(false);close.setBackgroundColor(0x00000000);
            close.setContentDescription("Close video and return to library");
            close.setOnClickListener(v->onExit.run());
            heading.addView(close,new LinearLayout.LayoutParams((int)(52*dp),(int)(52*dp)));
            final TextView videoTitle=new TextView(activity);
            videoTitle.setText(filename);videoTitle.setTextSize(16);
            videoTitle.setTextColor(-1);videoTitle.setSingleLine(true);
            videoTitle.setEllipsize(android.text.TextUtils.TruncateAt.END);
            heading.addView(videoTitle,new LinearLayout.LayoutParams(0,-2,1f));
            final Button share=new Button(activity);
            share.setText("↗");share.setTextColor(-1);share.setTextSize(20);
            share.setAllCaps(false);share.setBackgroundColor(0x00000000);
            share.setContentDescription("Share video with Android");
            share.setOnClickListener(v->{
                try{
                    android.content.Intent intent=new android.content.Intent(
                        android.content.Intent.ACTION_SEND);
                    intent.setType("video/*");
                    intent.putExtra(android.content.Intent.EXTRA_STREAM,original);
                    intent.addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    activity.startActivity(android.content.Intent.createChooser(intent,"Share video"));
                }catch(Exception e){showMessage("Cannot share this source");}
            });
            heading.addView(share,new LinearLayout.LayoutParams((int)(52*dp),(int)(52*dp)));
            root.addView(heading,new FrameLayout.LayoutParams(-1,(int)(58*dp),Gravity.TOP));
            final LinearLayout transport=new LinearLayout(activity);
            transport.setGravity(Gravity.CENTER);
            transport.setOrientation(LinearLayout.HORIZONTAL);
            final Button previous=new Button(activity);
            final Button toggle=new Button(activity);
            final Button next=new Button(activity);
            previous.setText("◀|");toggle.setText("Ⅱ");next.setText("|▶");
            for(Button b:new Button[]{previous,toggle,next}){
                b.setTextColor(-1);b.setTextSize(22);b.setAllCaps(false);
                b.setBackground(pill.getConstantState().newDrawable().mutate());
                b.setContentDescription(b==previous?"Previous video":
                    b==next?"Next video":"Play or pause");
                LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(
                    (int)((b==toggle?70:55)*dp),(int)((b==toggle?70:55)*dp));
                lp.setMargins((int)(12*dp),0,(int)(12*dp),0);
                transport.addView(b,lp);
            }
            previous.setOnClickListener(v->{if(mediaNavigator!=null)mediaNavigator.navigate(-1,false);});
            next.setOnClickListener(v->{if(mediaNavigator!=null)mediaNavigator.navigate(1,false);});
            toggle.setOnClickListener(v->{if(player.isPlaying())player.pause();else player.play();});
            root.addView(transport,new FrameLayout.LayoutParams(-2,-2,Gravity.CENTER));
            // Seek is separate from playlist navigation and never occluded.
            final LinearLayout footer=new LinearLayout(activity);
            footer.setOrientation(LinearLayout.VERTICAL);
            footer.setPadding((int)(14*dp),(int)(7*dp),(int)(14*dp),(int)(6*dp));
            footer.setBackgroundColor(0xbd101116);
            final LinearLayout timeline=new LinearLayout(activity);
            timeline.setGravity(Gravity.CENTER_VERTICAL);
            final TextView elapsed=new TextView(activity),duration=new TextView(activity);
            for(TextView time:new TextView[]{elapsed,duration}){
                time.setText("00:00");time.setTextColor(-1);time.setTextSize(13);
                time.setGravity(Gravity.CENTER);
            }
            final android.widget.SeekBar scrub=new android.widget.SeekBar(activity);
            scrub.setMax(1000);
            scrub.setProgressTintList(android.content.res.ColorStateList.valueOf(0xff7ec2cc));
            scrub.setThumbTintList(android.content.res.ColorStateList.valueOf(0xff7ec2cc));
            timeline.addView(elapsed,new LinearLayout.LayoutParams((int)(64*dp),-2));
            timeline.addView(scrub,new LinearLayout.LayoutParams(0,-2,1f));
            timeline.addView(duration,new LinearLayout.LayoutParams((int)(64*dp),-2));
            footer.addView(timeline,new LinearLayout.LayoutParams(-1,(int)(43*dp)));
            final LinearLayout modes=new LinearLayout(activity);
            modes.setGravity(Gravity.CENTER);
            final String[] modeNames={"Play next","Replay","Shuffle"};
            final Button[] modeButtons=new Button[3];
            for(int i=0;i<3;i++){
                final int selectedMode=i;
                final Button b=new Button(activity);
                b.setText(modeNames[i]);b.setTextSize(12);b.setAllCaps(false);
                b.setMinHeight(0);b.setMinimumHeight(0);
                b.setContentDescription("Playback mode: "+modeNames[i]);
                LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(0,(int)(38*dp),1f);
                params.setMargins((int)(3*dp),0,(int)(3*dp),0);
                modes.addView(b,params);
                modeButtons[i]=b;
                b.setOnClickListener(v->{playbackMode=selectedMode;refreshPlaybackMode(modeButtons);});
            }
            refreshPlaybackMode(modeButtons);
            footer.addView(modes,new LinearLayout.LayoutParams(-1,(int)(40*dp)));
            root.addView(footer,new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM));
            scrub.setOnSeekBarChangeListener(new android.widget.SeekBar.OnSeekBarChangeListener(){
                boolean dragging=false;
                @Override public void onStartTrackingTouch(android.widget.SeekBar b){dragging=true;}
                @Override public void onProgressChanged(android.widget.SeekBar b,int value,boolean fromUser){}
                @Override public void onStopTrackingTouch(android.widget.SeekBar b){
                    dragging=false;long end=player.getDuration();
                    if(end>0&&player.isCommandAvailable(Player.COMMAND_SEEK_IN_CURRENT_MEDIA_ITEM))
                        player.seekTo(end*b.getProgress()/1000L);
                }
            });
            final android.os.Handler handler=new android.os.Handler(android.os.Looper.getMainLooper());
            final Runnable[] clock={null};
            clock[0]=()->{
                if(closed)return;
                long ms=Math.max(0,player.getCurrentPosition()),end=player.getDuration();
                elapsed.setText(clockText(ms));duration.setText(clockText(Math.max(0,end)));
                toggle.setText(player.isPlaying()?"Ⅱ":"▶");
                if(end>0&&!scrub.isPressed())
                    scrub.setProgress((int)Math.min(1000,ms*1000L/end));
                handler.postDelayed(clock[0],350);
            };
            handler.post(clock[0]);
            // Two-finger gestures are left to the player; double tap seeks 10s.
            final View tapLayer=new View(activity);
            final GestureDetector detector=new GestureDetector(activity,
                new GestureDetector.SimpleOnGestureListener(){
                    @Override public boolean onDown(MotionEvent e){return true;}
                    @Override public boolean onSingleTapConfirmed(MotionEvent e){
                        int newVisibility=transport.getVisibility()==View.VISIBLE?
                            View.GONE:View.VISIBLE;
                        transport.setVisibility(newVisibility);
                        heading.setVisibility(newVisibility);
                        footer.setVisibility(newVisibility);
                        return true;
                    }
                    @Override public boolean onDoubleTap(MotionEvent e){
                        if(!player.isCommandAvailable(Player.COMMAND_SEEK_IN_CURRENT_MEDIA_ITEM))return true;
                        long amount=e.getX()<root.getWidth()/2?-10000:10000;
                        long position=Math.max(0,player.getCurrentPosition()+amount);
                        if(player.getDuration()>0)position=Math.min(position,player.getDuration());
                        player.seekTo(position);return true;
                    }
                });
            tapLayer.setOnTouchListener((v,e)->detector.onTouchEvent(e));
            // Gesture layer is behind all buttons, so playback actions stay clickable.
            root.addView(tapLayer,1,new FrameLayout.LayoutParams(-1,-1));
'''
s=s[:start]+replacement+s[end:]
# Reduce buffering text overlap; share title and transport must not be occluded.
s=s.replace('video?(Gravity.BOTTOM|Gravity.CENTER_HORIZONTAL):Gravity.BOTTOM',
            'video?(Gravity.TOP|Gravity.CENTER_HORIZONTAL):Gravity.BOTTOM',1)
# Status is only a compact, temporary overlay below the title.
s=s.replace('''        player.addListener(new Player.Listener(){''',
'''        if(video){
            FrameLayout.LayoutParams lp=(FrameLayout.LayoutParams)status.getLayoutParams();
            lp.topMargin=(int)(65*activity.getResources().getDisplayMetrics().density);
            status.setLayoutParams(lp);
        }
        player.addListener(new Player.Listener(){''',1)
# Time counter used by native Aloha-style seek bar.
anchor='''    private static void refreshPlaybackMode(Button[] buttons){'''
assert s.count(anchor)==1
s=s.replace(anchor,'''    private static String clockText(long ms){
        long seconds=Math.max(0,ms/1000L);
        return String.format(java.util.Locale.ROOT,"%02d:%02d",
            seconds/60L,seconds%60L);
    }
'''+anchor,1)
path.write_text(s,encoding="utf-8")
print("VIDEO_LAYOUT_Aloha_STYLE_READY")
