import hashlib
import sys
import openslide
import json
import csv
import ntpath
import os
import os.path
import pandas as pd
import argparse
import uuid

error_info = {}
error_info["no_error"] = { "code":0, "msg":"no-error" }
error_info["image_file"] = { "code":201, "msg":"image-format-unsupported" }
error_info["openslide"] = { "code":202, "msg":"openslide-error" }
error_info["file_format"] = { "code":203, "msg":"file-format-error" }
error_info["missing_file"] = { "code":204, "msg":"missing-file" }
error_info["missing_columns"] = { "code":205, "msg":"missing-columns" }
error_info["manifest_errors"] = { "code":206, "msg":"manifest-errors" }

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
    ierr = error_info["no_error"];
    img  = None;
    img_json = None;
    if os.path.exists(fname): 
        try: 
            img = openslide.OpenSlide(fname); 
        except openslide.OpenSlideUnsupportedFormatError: 
            ierr = error_info["image_file"]; 
        except: 
            ierr = error_info["openslide"];
    else: # file does not exist
        ierr = error_info["missing_file"];

    img_meta = {};
    img_meta["error_info"] = ierr
    if str(ierr["code"]) == str(error_info["no_error"]["code"]):
       img_meta = package_metadata(img_meta,img);
    img_temp = json.dumps(img_meta);
    img_json = json.loads(img_temp);
    return img_json,img,ierr;

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

def write_macro_image(img_json,macro_rgb,label_rgb,thumb_rgb,fname):
    base_name = ntpath.basename(fname);
    if not os.path.exists(fname):
       os.makedirs(fname);
    fname_pre = fname + "/" + os.path.splitext(base_name)[0];

    out_metadata_json_fd = open(fname_pre+"-metadata.json","w");
    json.dump(img_json,out_metadata_json_fd);
    out_metadata_json_fd.close();

    if macro_rgb is not None:
       fname_out = fname_pre + "-macro.jpg";
       macro_rgb.save(fname_out);
    if label_rgb is not None:
       fname_out = fname_pre + "-label.jpg";
       label_rgb.save(fname_out);
    if thumb_rgb is not None:
       fname_out = fname_pre + "-thumb.jpg";
       thumb_rgb.save(fname_out);

parser = argparse.ArgumentParser(description="WSI metadata extractor.")
parser.add_argument("--inpmeta",nargs="?",default="quip_manifest.csv",type=str,help="input manifest (metadata) file.")
parser.add_argument("--errfile",nargs="?",default="quip_wsi_error_log.json",type=str,help="error log file.")
parser.add_argument("--inpdir",nargs="?",default="/data/images",type=str,help="input folder.")
parser.add_argument("--outdir",nargs="?",default="/data/output",type=str,help="output folder.")

def check_input_errors(pf,all_log):
    ret_val = 0;
    if "path" not in pf.columns:
        ierr = error_info["missing_columns"]
        ierr["msg"] = ierr["msg"]+": "+"path"
        all_log["error"].append(ierr)
        ret_val = 1

    if "file_uuid" not in pf.columns:
        ierr = error_info["missing_columns"] 
        ierr["msg"] = ierr["msg"]+": "+"file_uuid"
        all_log["error"].append(ierr)
        ret_val = 1
            
    if "manifest_error_code" not in pf.columns:
        ierr = error_info["missing_columns"] 
        ierr["msg"] = ierr["msg"]+": "+"manifest_error_code"
        all_log["error"].append(ierr)
        ret_val = 1

    if "manifest_error_msg" not in pf.columns:
        ierr = error_info["missing_columns"] 
        ierr["msg"] = ierr["msg"]+": "+"manifest_error_msg"
        all_log["error"].append(ierr)
        ret_val = 1

    return ret_val

def main(args):
    inp_folder   = args.inpdir
    out_folder   = args.outdir
    inp_manifest_fname = args.inpmeta 
    out_manifest_fname = inp_manifest_fname
    out_error_fname = args.errfile 

    out_error_fd = open(out_folder + "/" + out_error_fname,"w");
    all_log = {}
    all_log["error"] = []
    all_log["warning"] = [] 
    try:
        inp_metadata_fd = open(inp_folder + "/" + inp_manifest_fname);
    except OSError:
        ierr = error_info["missing_file"];
        ierr["msg"] = ierr["msg"]+": "+str(inp_manifest_fname)
        all_log["error"].append(ierr)
        json.dump(all_log,out_error_fd)
        out_error_fd.close()
        sys.exit(1)

    pfinp = pd.read_csv(inp_metadata_fd,sep=',')
    if check_input_errors(pfinp,all_log) != 0:
        json.dump(all_log,out_error_fd);
        out_error_fd.close();
        inp_metadata_fd.close();
        sys.exit(1);
 
    out_metadata_fd = open(out_folder + "/" + out_manifest_fname,"w");
    cols  = ['file_uuid','slide_error_msg','slide_error_code'];
    pfout = pd.DataFrame(columns=cols);
    for file_idx in range(len(pfinp["path"])):
        file_uuid = pfinp["file_uuid"][file_idx];
        pfout.at[file_idx,"file_uuid"] = file_uuid;
        pfout.at[file_idx,"slide_error_code"] = str(error_info["no_error"]["code"]);
        pfout.at[file_idx,"slide_error_msg"]  = error_info["no_error"]["msg"]; 
        if str(pfinp["manifest_error_code"][file_idx])!=str(error_info["no_error"]["code"]):
            pfout.at[file_idx,"file_uuid"] = file_uuid;
            pfout.at[file_idx,"slide_error_code"] = str(error_info["manifest_errors"]["code"]);
            pfout.at[file_idx,"slide_error_msg"] = error_info["manifest_errors"]["msg"]; 
            ierr["row_idx"] = file_idx
            ierr["file_uuid"] = file_uuid
            all_log["error"].append(ierr) 
        else: # Extract metadata from image
            fname = inp_folder+"/"+pfinp["path"][file_idx];
            img_json,img,ierr = openslide_metadata(fname);
            img_json["filename"] = file_uuid; 
            if str(ierr["code"])!=str(error_info["no_error"]["code"]):
                ierr["row_idx"] = file_idx
                ierr["file_uuid"] = file_uuid
                all_log["error"].append(ierr) 
                pfout.at[file_idx,"file_uuid"] = file_uuid;
                pfout.at[file_idx,"slide_error_code"] = str(ierr["code"]);
                pfout.at[file_idx,"slide_error_msg"] = ierr["msg"];
 
            # If file is OK, extract macro image and write it out
            if str(ierr["code"])==str(error_info["no_error"]["code"]):
                macro_rgb,label_rgb,thumb_rgb = extract_macro_image(img);
                write_macro_image(img_json,macro_rgb,label_rgb,thumb_rgb,out_folder+"/"+file_uuid);

    pfout.to_csv(out_metadata_fd,index=False)
    json.dump(all_log,out_error_fd)

    inp_metadata_fd.close();
    out_error_fd.close()
    out_metadata_fd.close();

if __name__ == "__main__":
    args = parser.parse_args() 
    main(args)

