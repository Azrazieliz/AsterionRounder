#!/usr/bin/env python3
"""v0.15.13: restore slim premium video controls, immersive crop and pinch zoom."""
from pathlib import Path
import re
root=Path("app")
file=root/"src/main/java/com/openlocal/office/core/FgMediaPlayer.java"
s=file.read_text(encoding="utf-8")
def one(old,new,label):
 global s
 n=s.count(old)
 if n!=1:raise RuntimeError(f"{label}: found {n} expected exactly once")
 s=s.replace(old,new,1)
one("display.setUseController(false);",
    "display.setUseController(false);\n            display.setResizeMode(androidx.media3.ui.AspectRatioFrameLayout.RESIZE_MODE_ZOOM);",
    "full bleed default crop")
one("root.setBackgroundColor(0xff090c13);","root.setBackgroundColor(0xff000000);","true fullscreen background")
one("heading.setBackgroundColor(0xc40d0d12);",
    """heading.setBackground(new android.graphics.drawable.GradientDrawable(
                android.graphics.drawable.GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{0xb5000000,0x42000000,0x00000000}));""","top overlay fade")
one("heading.setPadding((int)(12*dp),0,(int)(10*dp),0);",
    "heading.setPadding((int)(7*dp),0,(int)(8*dp),0);","compact top margins")
one("close.setText(\"×\");close.setTextColor(-1);close.setTextSize(24);",
    "close.setText(\"×\");close.setTextColor(-1);close.setTextSize(22);","close size")
one("videoTitle.setText(filename);videoTitle.setTextSize(16);",
    "videoTitle.setText(filename);videoTitle.setTextSize(15);","video title")
start=s.index("            final TextView orientation=smallChromeIcon(")
end=s.index("            FrameLayout.LayoutParams headPosition=",start)
replacement=r'''            // Native vector phone / padlock icons, never diamond or share.
            final View orientation=new View(activity){
                final android.graphics.Paint p=new android.graphics.Paint(3);
                @Override protected void onDraw(android.graphics.Canvas c){
                    super.onDraw(c);
                    float u=activity.getResources().getDisplayMetrics().density;
                    float cx=getWidth()/2f,cy=getHeight()/2f;
                    boolean horizontal=(selectedRotation[0]==2||
                        (selectedRotation[0]==0&&!verticalSource[0]));
                    c.save();
                    if(horizontal)c.rotate(90,cx,cy);
                    p.setColor(0xfff0f4ff);p.setStrokeWidth(1.9f*u);
                    p.setStyle(android.graphics.Paint.Style.STROKE);
                    c.drawRoundRect(cx-8*u,cy-12*u,cx+8*u,cy+12*u,3*u,3*u,p);
                    c.drawLine(cx-4*u,cy-8.5f*u,cx+4*u,cy-8.5f*u,p);
                    p.setStyle(android.graphics.Paint.Style.FILL);
                    c.drawCircle(cx,cy+9*u,1.2f*u,p);
                    c.restore();
                }
            };
            orientation.setClickable(true);orientation.setFocusable(true);
            orientation.setContentDescription("Phone orientation. Tap for portrait or landscape.");
            final View lock=new View(activity){
                final android.graphics.Paint p=new android.graphics.Paint(3);
                @Override protected void onDraw(android.graphics.Canvas c){
                    super.onDraw(c);
                    float u=activity.getResources().getDisplayMetrics().density;
                    float cx=getWidth()/2f,cy=getHeight()/2f;
                    p.setColor(0xffeff5ff);p.setStrokeWidth(2*u);
                    p.setStrokeCap(android.graphics.Paint.Cap.ROUND);
                    p.setStyle(android.graphics.Paint.Style.STROKE);
                    c.drawArc(cx-6*u,cy-10*u,cx+6*u,cy+4*u,185,170,false,p);
                    p.setStyle(android.graphics.Paint.Style.FILL);
                    c.drawRoundRect(cx-10*u,cy-2*u,cx+10*u,cy+12*u,2.5f*u,2.5f*u,p);
                    p.setColor(0xff101924);
                    c.drawCircle(cx,cy+3*u,1.9f*u,p);
                    c.drawRect(cx-.8f*u,cy+4*u,cx+.8f*u,cy+8*u,p);
                    if(rotationLocked[0]){
                        p.setColor(0xff87c6d1);
                        p.setStyle(android.graphics.Paint.Style.STROKE);
                        p.setStrokeWidth(1.6f*u);
                        c.drawCircle(cx,cy+4*u,14*u,p);
                    }
                }
            };
            lock.setClickable(true);lock.setFocusable(true);
            lock.setContentDescription("Lock video orientation");
            orientation.setOnClickListener(v->{
                selectedRotation[0]= selectedRotation[0]==2?1:2;
                rotationLocked[0]=false;
                applyRotation.run();
                orientation.invalidate();lock.invalidate();
                orientation.setContentDescription(selectedRotation[0]==1?
                    "Phone portrait orientation":"Phone landscape orientation");
            });
            lock.setOnClickListener(v->{
                rotationLocked[0]=!rotationLocked[0];
                applyRotation.run();
                lock.invalidate();
                lock.setContentDescription(rotationLocked[0]?
                    "Unlock orientation":"Lock orientation");
            });
            heading.addView(orientation,new LinearLayout.LayoutParams((int)(44*dp),(int)(48*dp)));
            heading.addView(lock,new LinearLayout.LayoutParams((int)(44*dp),(int)(48*dp)));
'''
s=s[:start]+replacement+s[end:]
one("headPosition.rightMargin=(int)(55*dp);","headPosition.rightMargin=(int)(12*dp);","no abandoned share area")
one("final LinearLayout transport=new LinearLayout(activity);",
    "final long[] lastChromeInteraction={android.os.SystemClock.uptimeMillis()};\n            final LinearLayout transport=new LinearLayout(activity);",
    "declare chrome before listeners")
one("            final long[] lastChromeInteraction={android.os.SystemClock.uptimeMillis()};\n            final LinearLayout footer=new LinearLayout(activity);",
    "            final LinearLayout footer=new LinearLayout(activity);","avoid duplicate chrome")
# Give clean native vector controls rather than broken font glyphs.
start=s.index("            final Button previous=new Button(activity);")
end=s.index("            root.addView(transport,new FrameLayout.LayoutParams(-2,-2,Gravity.CENTER));",start)
new=r'''            final VideoTransport previous=new VideoTransport(activity,0,dp);
            final VideoTransport toggle=new VideoTransport(activity,1,dp);
            final VideoTransport next=new VideoTransport(activity,2,dp);
            for(VideoTransport button:new VideoTransport[]{previous,toggle,next}){
                button.setContentDescription(button==previous?"Previous video":
                    button==next?"Next video":"Play or pause");
                int size=button==toggle?60:48;
                LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(
                    (int)(size*dp),(int)(size*dp));
                lp.setMargins((int)(5*dp),0,(int)(5*dp),0);
                transport.addView(button,lp);
            }
            previous.setOnClickListener(v->{
                lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();
                if(mediaNavigator!=null)mediaNavigator.navigate(-1,false);
            });
            next.setOnClickListener(v->{
                lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();
                if(mediaNavigator!=null)mediaNavigator.navigate(1,false);
            });
            toggle.setOnClickListener(v->{
                lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();
                if(player.isPlaying())player.pause();else player.play();
                toggle.invalidate();
            });
'''
s=s[:start]+new+s[end:]
one("toggle.setText(player.isPlaying()?\"Ⅱ\":\"▶\");",
    "toggle.setPlaying(player.isPlaying());","native play icon state")
one("footerPosition.rightMargin=(int)(65*dp);",
    "footerPosition.rightMargin=(int)(20*dp);","less intrusive right inset")
one("footerPosition.bottomMargin=(int)(8*dp);",
    "footerPosition.bottomMargin=(int)(12*dp);","nav safe bottom inset")
one("            // Two-finger gestures are left to the player; double tap seeks 10s.\n            final View tapLayer=new View(activity);",
"""            // 1x means edge-to-edge cropped video, not fitted pillarboxes.
            // Pinch up to 4x and pan when magnified; double tap center resets.
            final float[] videoScale={1f},videoX={0f},videoY={0f};
            final Runnable applyZoom=()->{
                float scale=videoScale[0];
                float maxX=Math.max(0,(root.getWidth()*(scale-1))/2f);
                float maxY=Math.max(0,(root.getHeight()*(scale-1))/2f);
                videoX[0]=Math.max(-maxX,Math.min(maxX,videoX[0]));
                videoY[0]=Math.max(-maxY,Math.min(maxY,videoY[0]));
                display.setPivotX(display.getWidth()/2f);
                display.setPivotY(display.getHeight()/2f);
                display.setScaleX(scale);display.setScaleY(scale);
                display.setTranslationX(videoX[0]);display.setTranslationY(videoY[0]);
            };
            final android.view.ScaleGestureDetector scaler=
                new android.view.ScaleGestureDetector(activity,
                    new android.view.ScaleGestureDetector.SimpleOnScaleGestureListener(){
                        @Override public boolean onScale(android.view.ScaleGestureDetector detector){
                            videoScale[0]=Math.max(1f,Math.min(4f,
                                videoScale[0]*detector.getScaleFactor()));
                            if(videoScale[0]<1.02f){
                                videoScale[0]=1f;videoX[0]=0;videoY[0]=0;
                            }
                            applyZoom.run();return true;
                        }
                    });
            final float[] lastPan={0f,0f};
            final View tapLayer=new View(activity);""","pinch zoom")
one("""                        if(!player.isCommandAvailable(Player.COMMAND_SEEK_IN_CURRENT_MEDIA_ITEM))return true;
                        long amount=e.getX()<root.getWidth()/2?-10000:10000;""",
"""                        if(videoScale[0]>1.02f ||
                           (e.getX()>=root.getWidth()*.33f&&
                            e.getX()<=root.getWidth()*.67f)){
                            videoScale[0]=1f;videoX[0]=0f;videoY[0]=0f;
                            applyZoom.run();
                            return true;
                        }
                        if(!player.isCommandAvailable(Player.COMMAND_SEEK_IN_CURRENT_MEDIA_ITEM))return true;
                        long amount=e.getX()<root.getWidth()/2?-10000:10000;""","double tap zoom reset and side skip")
one("tapLayer.setOnTouchListener((v,e)->detector.onTouchEvent(e));",
"""tapLayer.setOnTouchListener((v,e)->{
                scaler.onTouchEvent(e);
                int action=e.getActionMasked();
                if(action==MotionEvent.ACTION_DOWN){
                    lastPan[0]=e.getX();lastPan[1]=e.getY();
                }else if(action==MotionEvent.ACTION_MOVE&&e.getPointerCount()==1&&
                         !scaler.isInProgress()&&videoScale[0]>1.02f){
                    videoX[0]+=e.getX()-lastPan[0];
                    videoY[0]+=e.getY()-lastPan[1];
                    applyZoom.run();
                }
                if(e.getPointerCount()==1){
                    lastPan[0]=e.getX();lastPan[1]=e.getY();
                }
                return scaler.isInProgress() || detector.onTouchEvent(e) ||
                       videoScale[0]>1.02f;
            });""","zoom and pan touch")
# Auto orientation follows aspect after media metadata, but no forced landscape before size known.
one("activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);",
    "activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);",
    "respect source orientation")
# Stylized native transport, no external fonts or custom assets.
anchor="    private TextView smallChromeIcon(String glyph,String description,float density){"
assert s.count(anchor)==1
video_class=r'''    private static final class VideoTransport extends View{
        private final int role;
        private final float dp;
        private boolean playing;
        private final android.graphics.Paint paint=new android.graphics.Paint(3);
        VideoTransport(Activity context,int role,float dp){
            super(context);this.role=role;this.dp=dp;
            setClickable(true);setFocusable(true);
        }
        void setPlaying(boolean value){if(playing!=value){playing=value;invalidate();}}
        @Override protected void onDraw(android.graphics.Canvas c){
            super.onDraw(c);
            float cx=getWidth()/2f,cy=getHeight()/2f;
            paint.setStyle(android.graphics.Paint.Style.FILL);
            paint.setColor(role==1?0xc51b2533:0xa7161d2a);
            c.drawCircle(cx,cy,Math.min(getWidth(),getHeight())*.49f,paint);
            paint.setColor(0xfff7f9ff);
            float t=role==1?11*dp:9*dp;
            if(role==1&&playing){
                c.drawRoundRect(cx-t*.62f,cy-t,cx-t*.15f,cy+t,1.2f*dp,1.2f*dp,paint);
                c.drawRoundRect(cx+t*.15f,cy-t,cx+t*.62f,cy+t,1.2f*dp,1.2f*dp,paint);
            }else{
                android.graphics.Path path=new android.graphics.Path();
                if(role==0){
                    path.moveTo(cx-t*.45f,cy);path.lineTo(cx+t*.55f,cy-t*.8f);
                    path.lineTo(cx+t*.55f,cy+t*.8f);path.close();
                    c.drawPath(path,paint);
                    c.drawRoundRect(cx-t*.8f,cy-t*.9f,cx-t*.59f,cy+t*.9f,1*dp,1*dp,paint);
                }else{
                    path.moveTo(cx-t*.5f,cy-t*.84f);
                    path.lineTo(cx+t*.6f,cy);
                    path.lineTo(cx-t*.5f,cy+t*.84f);path.close();
                    c.drawPath(path,paint);
                    if(role==2)c.drawRoundRect(cx+t*.66f,cy-t*.9f,
                        cx+t*.88f,cy+t*.9f,1*dp,1*dp,paint);
                }
            }
        }
    }
'''
s=s.replace(anchor,video_class+anchor,1)
file.write_text(s,encoding="utf-8")
print("PREMIUM_PLAYER_PHONE_LOCK_FULL_BLEED_PINCH_ZOOM_READY")
