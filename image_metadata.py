import hashlib
import sys
import openslide
import json
import csv
import ntpath
import os
import os.path
import pandas as pd

openslide_no_error=0
openslide_no_error_msg="openslide-no-error"
openslide_format_error=1
openslide_format_error_msg="openslide-format-error"
openslide_error=2
openslide_error_msg="openslide-error"
openslide_unknown_error=3
openslide_unknown_error_msg="openslide-unknown-error"

# compute md5sum hash of image file
def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Extract openslide metadata from image file
def package_metadata(img_meta,img):
    img_meta["level_count"] = int(img.level_count);
    img_meta["width"]  = img.dimensions[0];
    img_meta["height"] = img.dimensions[1];
 
    img_prop = img.properties;
    img_meta["vendor"] = "unknown" 
    img_meta["objective_power"] = "unknown";
    img_meta["mpp_x"] = float(-1.0);
    img_meta["mpp_y"] = float(-1.0);
    if openslide.PROPERTY_NAME_VENDOR in img_prop:
       img_meta["vendor"] = img_prop[openslide.PROPERTY_NAME_VENDOR];
    if openslide.PROPERTY_NAME_OBJECTIVE_POWER in img_prop:
       img_meta["objective_power"] = img_prop[openslide.PROPERTY_NAME_OBJECTIVE_POWER];
    if openslide.PROPERTY_NAME_MPP_X in img_prop:
       img_meta["mpp_x"] = float(img_prop[openslide.PROPERTY_NAME_MPP_X]);
    if openslide.PROPERTY_NAME_MPP_Y in img_prop:
       img_meta["mpp_y"] = float(img_prop[openslide.PROPERTY_NAME_MPP_Y]);
    img_meta_prop = {}
    for p in img_prop:
        img_meta_prop[p] = img_prop[p];
    img_meta["properties"] = img_meta_prop;
    return img_meta;

def openslide_metadata(fname):
    ierr_code = openslide_no_error;
    ierr_msg  = openslide_no_error_msg;
    img = None;
    try:
        img = openslide.OpenSlide(fname);
    except openslide.OpenSlideUnsupportedFormatError:
        ierr_code = openslide_format_error;
        ierr_msg  = openslide_format_error_msg;
    except openslide.OpenSlideError:
        ierr_code = openslide_error;
        ierr_msg  = openslide_error_msg;
    except:
        ierr_code = openslide_unknown_error;
        ierr_msg  = openslide_unknown_error_msg;

    img_meta = {};
    img_meta["error_code"] = ierr_code
    img_meta["error_msg"]  = ierr_msg
    if ierr_code == openslide_no_error:
       img_meta = package_metadata(img_meta,img);
    img_temp = json.dumps(img_meta);
    img_json = json.loads(img_temp);
    return img_json,img,ierr_code,ierr_msg;

def extract_macro_image(img):
    img_rgba  = img.associated_images;
    macro_rgb = None;
    label_rgb = None;
    thumb_rgb = None;
    if img_rgba != None:
       if "macro" in img_rgba:
          macro_rgb = img_rgba["macro"].convert("RGB");
       if "label" in img_rgba:
          label_rgb = img_rgba["label"].convert("RGB");
       if "thumbnail" in img_rgba:
          thumb_rgb = img_rgba["thumbnail"].convert("RGB");
       else:
          img_w = img.level_dimensions[img.level_count-1][0]
          img_h = img.level_dimensions[img.level_count-1][1]
          div_v = float(256/img_w)
          img_w = int(img_w*div_v)
          img_h = int(img_h*div_v)
          thumb_rgb = img.get_thumbnail((img_w,img_h)).convert("RGB"); 
    return macro_rgb,label_rgb,thumb_rgb;

def write_macro_image(macro_rgb,label_rgb,thumb_rgb,fname,file_uuid):
    base_name = ntpath.basename(fname);
    dest_folder = out_folder + fname + "/";
    if not os.path.exists(dest_folder):
       os.makedirs(dest_folder);
    fname_pre = dest_folder + os.path.splitext(base_name)[0];
    if macro_rgb:
       fname_out = fname_pre + "-macro.jpg";
       macro_rgb.save(fname_out);
    if label_rgb:
       fname_out = fname_pre + "-label.jpg";
       label_rgb.save(fname_out);
    if thumb_rgb:
       fname_out = fname_pre + "-thumb.jpg";
       thumb_rgb.save(fname_out);

def main(argv):
    inp_folder="/data/images/"
    out_folder="/data/output/"
    out_metadata_json="quip_metadata.json"
    inp_manifest = "quip_manifest.csv"
    if len(argv)==1:
       inp_manifest = argv[0]
    out_manifest = inp_manifest

    inp_file = open(inp_folder + "/" + inp_manifest);
    pf = pd.read_csv(inp_file,sep=',')
    if "path" not in pf.columns:
        print("ERROR: Header is missing in file: ",inp_manifest)
        inp_file.close()
        sys.exit(1);
    if "file_uuid" not in pf.columns:
        print("ERROR: file_uuid is missing in file: ",inp_manifest)
        inp_file.close()
        sys.exit(1);
    if "row_status" not in pf.columns:
        print("ERROR: row_status is missing in file: ",inp_manifest)
        inp_file.close()
        sys.exit(1);

    out_json = open(out_folder + "/" + out_metadata_json,"w");
    out_csv  = open(out_folder + "/" + out_manifest,"w");

    pf["metadata_error_code"] = 0
    pf["metadata_error_msg"]  = ""
    for file_idx in range(len(pf["path"])):
       if pf["row_status"][file_idx]=="ok":
           file_row  = pf["path"][file_idx];
           file_uuid = pf["file_uuid"][file_idx];
           fname = inp_folder+file_row;
           print("Processing: ",fname)

           # Extract metadata from image
           img_json,img,ierr_code,ierr_msg = openslide_metadata(fname);
           img_json["filename"] = file_row;
           pf.at[file_idx,"metadata_error_code"] = ierr_code
           pf.at[file_idx,"metadata_error_msg"]  = ierr_msg 

           # output to json file
           json.dump(img_json,out_json);
           out_json.write("\n");

           # If file is OK, extract macro image and write it out
           if ierr_code==openslide_no_error:
              macro_rgb,label_rgb,thumb_rgb = extract_macro_image(img);
              write_macro_image(macro_rgb,label_rgb,thumb_rgb,file_row,file_uuid);
    pf.to_csv(out_csv,index=False)

    inp_file.close();
    out_json.close();
    out_csv.close();

if __name__ == "__main__":
   main(sys.argv[1:])

