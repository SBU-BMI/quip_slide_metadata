import hashlib
import sys
import openslide
import json
import csv
import ntpath
import os
import os.path

inp_folder="/data/images/"
out_folder="/data/metadata/"
out_metadata_csv="metadata-out.csv"
out_metadata_json="metadata-out.json"

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
    ierr = 0;
    img = None;
    try:
        img = openslide.OpenSlide(fname);
    except openslide.OpenSlideUnsupportedFormatError:
        ierr = 1;
    except openslide.OpenSlideError:
        ierr = 2;
    except:
        ierr = 3;

    img_meta = {};
    if ierr == 1:
        img_meta["error"] = "format-error";
    elif ierr == 2:
        img_meta["error"] = "openslide-error";
    elif ierr == 3:
        img_meta["error"] = "unknown-error";
    elif ierr == 0:
        img_meta["error"] = "no-error";
        img_meta = package_metadata(img_meta,img);
    img_temp = json.dumps(img_meta);
    img_json = json.loads(img_temp);
    return img_json,img;

def extract_macro_image(img):
    img_rgba  = img.associated_images;
    print(img_rgba)
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
    return macro_rgb,label_rgb,thumb_rgb;

def write_macro_image(macro_rgb,label_rgb,thumb_rgb,fname):
    base_name = ntpath.basename(fname);
    if not os.path.exists(out_folder+fname):
       os.mkdir(out_folder+fname);
    fname_pre = os.path.splitext(base_name)[0];
    if macro_rgb:
       fname_out = out_folder + fname + "/" + fname_pre + "-macro.jpg";
       macro_rgb.save(fname_out);
    if label_rgb:
       fname_out = out_folder + fname + "/" + fname_pre + "-label.jpg";
       label_rgb.save(fname_out);
    if thumb_rgb:
       fname_out = out_folder + fname + "/" + fname_pre + "-thumb.jpg";
       thumb_rgb.save(fname_out);

def main(argv):
    inp_manifest="manifest.csv"
    if len(argv)!=0:
       inp_manifest = argv[0]
    inp_file = open(inp_folder + inp_manifest);
    out_json = open(out_folder + out_metadata_json,"w");
    out_csv  = open(out_folder + out_metadata_csv,"w");

    csv_reader = csv.reader(inp_file,delimiter=',')
    next(csv_reader) # skip header for now
    csv_writer = csv.writer(out_csv,delimiter=',') 
    for row in csv_reader:
        fname = inp_folder+row[0];
        print("Processing: ",fname)

        # Extract metadata from image
        img_json,img = openslide_metadata(fname);
        img_json["filename"] = row[0]; 

        # output to csv file
        csv_writer.writerow([row[0],img_json["error"]]);

        # output to json file
        json.dump(img_json,out_json);
        out_json.write("\n");

        # If file is OK, extract macro image and write it out
        if img_json["error"]=="no-error":
           macro_rgb,label_rgb,thumb_rgb = extract_macro_image(img);
           write_macro_image(macro_rgb,label_rgb,thumb_rgb,fname);

    inp_file.close();
    out_json.close();
    out_csv.close();

if __name__ == "__main__":
   main(sys.argv[1:])

