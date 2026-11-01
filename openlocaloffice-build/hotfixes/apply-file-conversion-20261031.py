#!/usr/bin/env python3
"""SAF conversion: image PNG/JPEG/WebP, single-page PDF render, CSV/TSV.
Never overwrite originals. ACTION_CREATE_DOCUMENT chooses every output."""
from pathlib import Path
p=Path("app/src/main/java/com/openlocal/office/MainActivity.java")
s=p.read_text()
anchor="    private static final int REQ_LIBRARY_TRANSFER = 2012;"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n    private static final int REQ_FG_CONVERT = 2013;",1)
anchor="    private volatile Uri fgTransferSource;"
assert s.count(anchor)==1
s=s.replace(anchor,'''    private volatile Uri fgConvertSource;
    private volatile String fgConvertFormat;
    private static String fgConvertMime(String format){
        switch(format){
            case "png":return "image/png";
            case "jpeg":return "image/jpeg";
            case "webp":return "image/webp";
            case "pdf":return "application/pdf";
            case "csv":return "text/csv";
            case "tsv":return "text/tab-separated-values";
            default:return null;
        }
    }
    private void selectConversionOutput(String sourceUri,String format){
        if(sourceUri==null||!allowedLibraryUris.contains(sourceUri))return;
        if(fgConvertMime(format)==null)return;
        Uri source=Uri.parse(sourceUri);
        String name=displayName(source);
        if(name==null||name.isBlank())return;
        String lower=name.toLowerCase(java.util.Locale.ROOT);
        boolean image=lower.endsWith(".png")||lower.endsWith(".jpeg")||
            lower.endsWith(".jpg")||lower.endsWith(".bmp")||lower.endsWith(".webp");
        boolean document=lower.endsWith(".pdf");
        boolean table=lower.endsWith(".csv")||lower.endsWith(".tsv");
        if(!(image&&java.util.Arrays.asList("png","jpeg","webp","pdf").contains(format)||
             document&&"png".equals(format)||
             table&&("csv".equals(format)||"tsv".equals(format))))return;
        fgConvertSource=source;fgConvertFormat=format;
        String clean=name.replaceFirst("[.][^.]+$","");
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.setType(fgConvertMime(format));
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.putExtra(Intent.EXTRA_TITLE,clean+"-converted."+format);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|
            Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        startActivityForResult(intent,REQ_FG_CONVERT);
    }
    private void convertDocument(Uri destination){
        final Uri source=fgConvertSource;
        final String format=fgConvertFormat;
        fgConvertSource=null;fgConvertFormat=null;
        if(source==null||destination==null||format==null)return;
        io.execute(()->{
            try{
                String low=displayName(source).toLowerCase(java.util.Locale.ROOT);
                if(low.endsWith(".csv")||low.endsWith(".tsv")){
                    char from=low.endsWith(".csv")?',':(char)9;
                    char to="csv".equals(format)?',':(char)9;
                    try(java.io.Reader input=new java.io.BufferedReader(
                             new java.io.InputStreamReader(
                                 getContentResolver().openInputStream(source),
                                 java.nio.charset.StandardCharsets.UTF_8),65536);
                        java.io.Writer output=new java.io.BufferedWriter(
                             new java.io.OutputStreamWriter(
                                 getContentResolver().openOutputStream(destination,"wt"),
                                 java.nio.charset.StandardCharsets.UTF_8),65536)){
                        boolean quoted=false;
                        for(int c;(c=input.read())!=-1;){
                            if(c=='"'){quoted=!quoted;output.write(c);}
                            else output.write(!quoted&&c==from?to:c);
                        }
                    }
                }else{
                    android.graphics.Bitmap bitmap;
                    if(low.endsWith(".pdf")){
                        try(android.os.ParcelFileDescriptor fd=
                            getContentResolver().openFileDescriptor(source,"r");
                            android.graphics.pdf.PdfRenderer renderer=
                                new android.graphics.pdf.PdfRenderer(fd);
                            android.graphics.pdf.PdfRenderer.Page page=renderer.openPage(0)){
                            int w=Math.max(1,page.getWidth()),h=Math.max(1,page.getHeight());
                            double scale=Math.min(2.0,Math.sqrt(12000000.0/(w*(double)h)));
                            bitmap=android.graphics.Bitmap.createBitmap(
                                Math.max(1,(int)(w*scale)),Math.max(1,(int)(h*scale)),
                                android.graphics.Bitmap.Config.ARGB_8888);
                            bitmap.eraseColor(android.graphics.Color.WHITE);
                            page.render(bitmap,null,null,
                                android.graphics.pdf.PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                        }
                    }else{
                        android.graphics.BitmapFactory.Options opts=
                            new android.graphics.BitmapFactory.Options();
                        opts.inJustDecodeBounds=true;
                        try(InputStream in=getContentResolver().openInputStream(source)){
                            android.graphics.BitmapFactory.decodeStream(in,null,opts);
                        }
                        if(opts.outWidth<1||opts.outHeight<1)
                            throw new IOException("Source is not a supported bitmap");
                        int sample=1;
                        while((opts.outWidth/sample)>6144||
                            (opts.outHeight/sample)>6144||
                            ((opts.outWidth/(double)sample)*(opts.outHeight/sample)>25000000))
                            sample*=2;
                        opts.inJustDecodeBounds=false;opts.inSampleSize=sample;
                        try(InputStream in=getContentResolver().openInputStream(source)){
                            bitmap=android.graphics.BitmapFactory.decodeStream(in,null,opts);
                        }
                    }
                    if(bitmap==null)throw new IOException("Image conversion could not decode source");
                    try{
                        if("pdf".equals(format)){
                            android.graphics.pdf.PdfDocument pdf=
                                new android.graphics.pdf.PdfDocument();
                            android.graphics.pdf.PdfDocument.PageInfo pageInfo=
                                new android.graphics.pdf.PdfDocument.PageInfo.Builder(
                                    bitmap.getWidth(),bitmap.getHeight(),1).create();
                            android.graphics.pdf.PdfDocument.Page page=pdf.startPage(pageInfo);
                            page.getCanvas().drawBitmap(bitmap,0f,0f,null);
                            pdf.finishPage(page);
                            try(java.io.OutputStream output=
                                getContentResolver().openOutputStream(destination,"wt")){
                                pdf.writeTo(output);
                            }finally{pdf.close();}
                        }else{
                            android.graphics.Bitmap.CompressFormat cf=
                                "png".equals(format)?android.graphics.Bitmap.CompressFormat.PNG:
                                "webp".equals(format)?android.graphics.Bitmap.CompressFormat.WEBP_LOSSY:
                                android.graphics.Bitmap.CompressFormat.JPEG;
                            try(java.io.OutputStream output=
                                getContentResolver().openOutputStream(destination,"wt")){
                                if(output==null||!bitmap.compress(cf,92,output))
                                    throw new IOException("Image encoder failed");
                            }
                        }
                    }finally{bitmap.recycle();}
                }
                final String ok="Converted to "+format.toUpperCase(java.util.Locale.ROOT)+
                    ". Original preserved.";
                final String successJson=new org.json.JSONObject()
                    .put("operation","convert").put("ok",true)
                    .put("detail",ok).toString();
                runOnUiThread(()->js("window.FileGestionerLibrary?.operationResult("+
                    successJson+")"));
                android.util.Log.i("FG_CONVERT","CONVERT_OK format="+format);
            }catch(Exception e){
                android.util.Log.e("FG_CONVERT","CONVERT_ERROR",e);
                final String msg=message(e);
                runOnUiThread(()->{
                    try{
                        js("window.FileGestionerLibrary?.operationResult("+
                            new org.json.JSONObject().put("operation","convert")
                                .put("ok",false).put("detail",msg).toString()+")");
                    }catch(Exception ignored){}
                });
            }
        });
    }
'''+anchor,1)
anchor="        if(requestCode==REQ_LIBRARY_TRANSFER){"
assert s.count(anchor)==1
s=s.replace(anchor,'''        if(requestCode==REQ_FG_CONVERT){
            convertDocument(uri);
            return;
        }
'''+anchor,1)
anchor="        @JavascriptInterface public void copyLibraryFile(String value){"
assert s.count(anchor)==1
s=s.replace(anchor,'''        @JavascriptInterface public void convertLibraryFile(String value,String format){
            runOnUiThread(()->selectConversionOutput(value,format));
        }
'''+anchor,1)
p.write_text(s)
print("Native conversion registered (images, PDF first page, CSV/TSV)")
