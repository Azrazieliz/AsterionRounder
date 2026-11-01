#!/usr/bin/env python3
"""Rounder video: clickable vector playback mode, safe right inset, rotation and lock."""
from pathlib import Path
p=Path("app/src/main/java/com/openlocal/office/core/FgMediaPlayer.java")
s=p.read_text(encoding="utf-8")
def one(a,b,title):
 global s
 n=s.count(a)
 if n!=1:raise RuntimeError(f"{title}: {n} occurrences")
 s=s.replace(a,b,1)
one("final LinearLayout heading=new LinearLayout(activity);",
"""final int[] selectedRotation={0}; // 0: video aspect auto, 1: portrait, 2: landscape
            final boolean[] rotationLocked={false},verticalSource={false};
            final Runnable applyRotation=()->{
                int requested=rotationLocked[0]?
                    ActivityInfo.SCREEN_ORIENTATION_LOCKED:
                    selectedRotation[0]==1?ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT:
                    selectedRotation[0]==2?ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE:
                    verticalSource[0]?ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT:
                    ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE;
                if(activity.getRequestedOrientation()!=requested)
                    activity.setRequestedOrientation(requested);
                activity.getWindow().getDecorView().postDelayed(()->{
                    if(!closed)forceImmersiveBars();
                },220);
            };
            final LinearLayout heading=new LinearLayout(activity);""","rotation controller")
one("heading.addView(videoTitle,new LinearLayout.LayoutParams(0,-2,1f));",
"""heading.addView(videoTitle,new LinearLayout.LayoutParams(0,-2,1f));
            final TextView orientation=smallChromeIcon("⟳","Rotation: automatic",dp);
            final TextView lock=smallChromeIcon("◇","Lock video orientation",dp);
            orientation.setOnClickListener(v->{
                rotationLocked[0]=false;
                selectedRotation[0]=(selectedRotation[0]+1)%3;
                orientation.setContentDescription("Rotation: "+(selectedRotation[0]==0?
                    "follow video":selectedRotation[0]==1?"portrait":"landscape"));
                lock.setText("◇");
                applyRotation.run();
            });
            lock.setOnClickListener(v->{
                rotationLocked[0]=!rotationLocked[0];
                lock.setText(rotationLocked[0]?"◆":"◇");
                lock.setContentDescription(rotationLocked[0]?
                    "Unlock video orientation":"Lock video orientation");
                applyRotation.run();
            });
            heading.addView(orientation,new LinearLayout.LayoutParams((int)(42*dp),(int)(52*dp)));
            heading.addView(lock,new LinearLayout.LayoutParams((int)(42*dp),(int)(52*dp)));""","orientation and lock controls")
one("root.addView(heading,new FrameLayout.LayoutParams(-1,(int)(58*dp),Gravity.TOP));",
"""FrameLayout.LayoutParams headPosition=new FrameLayout.LayoutParams(-1,(int)(58*dp),Gravity.TOP);
            headPosition.rightMargin=(int)(55*dp);
            root.addView(heading,headPosition);""","safe top chrome")
start=s.index("            final TextView modeSymbol=new TextView(activity);")
end=s.index("            root.addView(footer,new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM));",start)
s=s[:start]+r'''            final View modeSymbol=new View(activity){
                final android.graphics.Paint paint=new android.graphics.Paint(3);
                @Override protected void onDraw(android.graphics.Canvas canvas){
                    super.onDraw(canvas);
                    float scale= getResources().getDisplayMetrics().density;
                    float cx=getWidth()/2f,cy=getHeight()/2f;
                    paint.setColor(0xfff1f5ff);paint.setStrokeWidth(2.3f*scale);
                    paint.setStyle(android.graphics.Paint.Style.STROKE);
                    paint.setStrokeCap(android.graphics.Paint.Cap.ROUND);
                    paint.setStrokeJoin(android.graphics.Paint.Join.ROUND);
                    float r=10*scale;
                    if(playbackMode==0){
                        paint.setStyle(android.graphics.Paint.Style.FILL);
                        android.graphics.Path arrow=new android.graphics.Path();
                        arrow.moveTo(cx-r*.65f,cy-r*.9f);
                        arrow.lineTo(cx+r*.45f,cy);
                        arrow.lineTo(cx-r*.65f,cy+r*.9f);arrow.close();
                        canvas.drawPath(arrow,paint);
                        paint.setStyle(android.graphics.Paint.Style.STROKE);
                        canvas.drawLine(cx+r*.8f,cy-r,cx+r*.8f,cy+r,paint);
                    }else if(playbackMode==1){
                        canvas.drawArc(cx-r,cy-r,cx+r,cy+r,38,300,false,paint);
                        paint.setStyle(android.graphics.Paint.Style.FILL);
                        android.graphics.Path arrow=new android.graphics.Path();
                        arrow.moveTo(cx+r*.95f,cy-r*.9f);
                        arrow.lineTo(cx+r*.95f,cy-r*.05f);
                        arrow.lineTo(cx+r*.05f,cy-r*.5f);arrow.close();
                        canvas.drawPath(arrow,paint);
                        paint.setStyle(android.graphics.Paint.Style.STROKE);
                        canvas.drawText("1",cx-r*.22f,cy+r*.33f,paint);
                    }else{
                        canvas.drawLine(cx-r,cy-r*.75f,cx+r,cy+r*.75f,paint);
                        canvas.drawLine(cx-r,cy+r*.75f,cx+r,cy-r*.75f,paint);
                        paint.setStyle(android.graphics.Paint.Style.FILL);
                        android.graphics.Path a=new android.graphics.Path();
                        a.moveTo(cx+r*.95f,cy+r*.75f);
                        a.lineTo(cx+r*.30f,cy+r*.75f);
                        a.lineTo(cx+r*.85f,cy+r*.15f);a.close();canvas.drawPath(a,paint);
                        android.graphics.Path b=new android.graphics.Path();
                        b.moveTo(cx+r*.95f,cy-r*.75f);
                        b.lineTo(cx+r*.30f,cy-r*.75f);
                        b.lineTo(cx+r*.85f,cy-r*.15f);b.close();canvas.drawPath(b,paint);
                    }
                }
            };
            modeSymbol.setClickable(true);
            modeSymbol.setFocusable(true);
            modeSymbol.setContentDescription("Playback mode: "+playbackModeName()+". Tap to change.");
            timeline.addView(modeSymbol,new LinearLayout.LayoutParams((int)(46*dp),(int)(43*dp)));
            modeSymbol.setOnClickListener(v->{
                lastChromeInteraction[0]=android.os.SystemClock.uptimeMillis();
                playbackMode=(playbackMode+1)%3;
                modeSymbol.invalidate();
                modeSymbol.setContentDescription("Playback mode: "+playbackModeName()+". Tap to change.");
                android.widget.Toast.makeText(activity,playbackModeName(),
                    android.widget.Toast.LENGTH_SHORT).show();
            });
'''+s[end:]
one("root.addView(footer,new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM));",
"""FrameLayout.LayoutParams footerPosition=
                new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM);
            // In landscape the right-edge system gesture/navigation area
            // remains reserved even when Android temporarily shows its taskbar.
            footerPosition.rightMargin=(int)(65*dp);
            footerPosition.leftMargin=(int)(8*dp);
            footerPosition.bottomMargin=(int)(8*dp);
            root.addView(footer,footerPosition);""","landscape nav safe inset")
one("            enterVideoFullscreen();",
"""            player.addListener(new Player.Listener(){
                @Override public void onVideoSizeChanged(androidx.media3.common.VideoSize size){
                    if(size.width>0&&size.height>0){
                        verticalSource[0]=size.height>size.width;
                        if(selectedRotation[0]==0&&!rotationLocked[0])applyRotation.run();
                    }
                }
            });
            enterVideoFullscreen();""","video size dynamic orientation")
one("    private void enterVideoFullscreen(){",
"""    private TextView smallChromeIcon(String glyph,String description,float density){
        TextView view=new TextView(activity);
        view.setText(glyph);
        view.setTextColor(0xffffffff);
        view.setTextSize(23);
        view.setGravity(Gravity.CENTER);
        view.setContentDescription(description);
        view.setBackgroundColor(0x00000000);
        view.setClickable(true);
        view.setFocusable(true);
        return view;
    }
    private void forceImmersiveBars(){
        activity.getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN|
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY|
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE|
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN|
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        if(android.os.Build.VERSION.SDK_INT>=30){
            android.view.WindowInsetsController controller=
                activity.getWindow().getInsetsController();
            if(controller!=null){
                controller.hide(android.view.WindowInsets.Type.statusBars()|
                    android.view.WindowInsets.Type.navigationBars());
                controller.setSystemBarsBehavior(
                    android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        }
    }
    private void enterVideoFullscreen(){""","modern fullscreen implementation")
one("""        activity.getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN |
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
    }
    private void leaveVideoFullscreen(){""",
"""        forceImmersiveBars();
    }
    private void leaveVideoFullscreen(){""","use modern fullscreen")
p.write_text(s,encoding="utf-8")
print("VIDEO_SAFE_ICON_ROTATE_LOCK_IMMERSIVE_READY")
