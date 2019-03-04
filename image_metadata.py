import hashlib
import sys
import openslide
import json
import csv

inp_folder="/data/"

# compute md5sum hash of image file
def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Extract openslide metadata from image file
def openslide_metadata(fname):
    ierr = 0;
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
    if ierr == 2:
        img_meta["error"] = "openslide-error";
    if ierr == 3:
        img_meta["error"] = "unknown-error";
    if ierr == 0:
        img_meta["error"] = "no-error";
        img_prop = img.properties;
        img_meta["vendor"] = img_prop["openslide.vendor"];
        img_meta["width"]  = img.dimensions[0];
        img_meta["height"] = img.dimensions[1];
        img_meta["objective_power"] = img_prop[openslide.PROPERTY_NAME_OBJECTIVE_POWER];
        img_meta["mpp_x"] = img_prop[openslide.PROPERTY_NAME_MPP_X];
        img_meta["mpp_y"] = img_prop[openslide.PROPERTY_NAME_MPP_Y];
        img_meta_prop = {}
        for p in img_prop:
            img_meta_prop[p] = img_prop[p];
        img_meta["properties"] = img_meta_prop;
    img_temp = json.dumps(img_meta);
    img_json = json.loads(img_temp);
    return img_json;

def main(argv):
    inp_file = open(argv[0]);
    out_json = open(argv[1],"w");
    out_csv  = open(argv[2],"w");

    csv_reader = csv.reader(inp_file, delimiter=',')
    csv_writer = csv.writer(out_csv,delimiter=',') 
    for row in csv_reader:
        fname = inp_folder+row[2];
        md5_val = md5(fname); 
        img_json = openslide_metadata(fname);
        img_json["subject_id"] = row[0];
        img_json["case_id"] = row[1];
        img_json["md5"] = md5_val;
        img_json["md5_error"] = "md5_ok";
        if (len(row)==4 and row[3]!="-1"):
            if row[3]!=md5_val:
                img_json["md5_error"] = "md5_error"; 
        else:
            img_json["md5_error"] = "md5_computed";
        if (len(row)==4 and row[3]!="-1"):
            csv_writer.writerow([row[0],row[1],row[2],row[3],img_json["error"],img_json["md5_error"]]);
        elif (len(row)==4 and row[3]=="-1"):
            csv_writer.writerow([row[0],row[1],row[2],md5_val,img_json["error"],img_json["md5_error"]]);
        else:
            csv_writer.writerow([row[0],row[1],row[2],md5_val,img_json["error"],img_json["md5_error"]]);
        json.dump(img_json,out_json);
        out_json.write("\n");
    inp_file.close();
    out_json.close();
    out_csv.close();


if __name__ == "__main__":
   main(sys.argv[1:])

