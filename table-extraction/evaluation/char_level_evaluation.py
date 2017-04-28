import argparse
import os
import numpy as np

from pdf.pdf_utils import normalize_pdf, analyze_pages
from utils.display_utils import display_bounding_boxes, pdf_to_img
from utils.bbox_utils import isContained
from wand.color import Color


DISPLAY_RESULTS = False


def get_words_in_bounding_boxes(extracted_bboxes, gt_bboxes, chars, page_num):
    if page_num in extracted_bboxes.keys():
        extracted_bbox = extracted_bboxes[page_num]
    else:
        extracted_bbox = []
    if page_num in gt_bboxes.keys():
        gt_bbox = gt_bboxes[page_num]
    else:
        gt_bbox = []
    extracted_chars = []
    gt_chars = []
    for i, c in enumerate(chars):
        try:
            if any([isContained((c.y0, c.x0, c.y1, c.x1), bbox) for bbox in extracted_bbox]):
                extracted_chars += [i]
            if any([isContained((c.y0, c.x0, c.y1, c.x1), bbox) for bbox in gt_bbox]):
                gt_chars += [i]
        except AttributeError:
            pass
    return extracted_chars, gt_chars


def compute_sub_objects_recall(extracted_chars, gt_chars):
    # tp / (tp + fn)
    tp = 0.0
    i = 0
    j = 0
    while i < len(extracted_chars) and j < len(gt_chars):
        if extracted_chars[i] == gt_chars[j]:
            tp += 1
            i += 1
            j += 1
        elif extracted_chars[i] < gt_chars[j]:
            i += 1
        else:
            j += 1
    return tp / len(gt_chars)


def compute_sub_objects_precision(extracted_chars, gt_chars):
    # tp / (tp + fp)
    tp = 0.0
    i = 0
    j = 0
    while i < len(extracted_chars) and j < len(gt_chars):
        if extracted_chars[i] == gt_chars[j]:
            tp += 1
            i += 1
            j += 1
        elif extracted_chars[i] < gt_chars[j]:
            i += 1
        else:
            j += 1
    return tp / len(extracted_chars)


def rescale(y0, x0, y1, x1, w_ratio, h_ratio):
    return int(y0*h_ratio), int(x0*w_ratio), int(y1*h_ratio), int(x1*w_ratio)


def get_bboxes_from_line(line, default_width=612.0, default_height=792.0):
    if line == "NO_TABLES":
        return {}
    bboxes = {}
    for bbox in line.split(";"):
        page_num, page_width, page_height, y0, x0, y1, x1 = bbox[1:-1].split(",")
        w_ratio = default_width/float(page_width)
        h_ratio = default_height/float(page_height)
        y0, x0, y1, x1 = rescale(float(y0), float(x0), float(y1), float(x1), w_ratio, h_ratio)
        try:
            bboxes[int(page_num)] += [(int(y0), int(x0), int(y1), int(x1))]
        except KeyError:
            bboxes[int(page_num)] = [(int(y0), int(x0), int(y1), int(x1))]
    return bboxes


def display_results(pdf_file, page_num, bbox, color, page_width=612, page_height=792,):
    try:
        bbox_in_page = bbox[page_num]
    except KeyError:
        bbox_in_page = []
    img = pdf_to_img(pdf_file, page_num, page_width, page_height)
    display_bounding_boxes(img, bbox_in_page, color=color)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="""Computes scores for the table localization task.
            Returns Recall and Precision for the sub-objects level (characters in text).
            If DISPLAY=TRUE, display GT in Red and extracted bboxes in Blue""")
    parser.add_argument("pdf_files", help="list of paths of PDF file to process")
    parser.add_argument("extracted_bbox", help="extracting bounding boxes (one line per pdf file)")
    parser.add_argument("gt_bbox", help="ground truth bounding boxes (one line per pdf file)")
    args = parser.parse_args()
    extracted_bbox_line = [bbox.rstrip() for bbox in open(args.extracted_bbox).readlines()]
    gt_bbox_line = [bbox.rstrip() for bbox in open(args.gt_bbox).readlines()]
    pdf_files = [pdf_file.rstrip() for pdf_file in open(args.pdf_files).readlines()]
    recall = []
    precision = []
    for i, pdf_file in enumerate(pdf_files):
        print "{} documents processed out of {}".format(i, len(pdf_files))
        extracted_bbox = get_bboxes_from_line(extracted_bbox_line[i])
        gt_bbox = get_bboxes_from_line(gt_bbox_line[i])
        for page_num, layout in enumerate(analyze_pages(os.environ['DATAPATH'] + pdf_file)):
            page_num += 1  # indexes start at 1
            elems, _ = normalize_pdf(layout, scaler=1)
            # We take the union of bboxes in a page and compare characters within bboxes
            extracted_chars, gt_chars = get_words_in_bounding_boxes(extracted_bbox, gt_bbox, elems.chars,
                                                                    page_num)
            if len(extracted_chars) > 0 and len(gt_chars) > 0:
                recall.append(compute_sub_objects_recall(extracted_chars, gt_chars))
                precision.append(compute_sub_objects_precision(extracted_chars, gt_chars))
            elif len(extracted_chars) == 0 and len(gt_chars) > 0:
                # There is a table that wasn't identified
                print "Table was not found in page {} of doc {}".format(page_num, pdf_file)
                recall.append(0.0)
            elif len(gt_chars) == 0 and len(extracted_chars) > 0:
                # There is no table but the method found a false positive
                print "Table was found in page {} of doc {} - error".format(page_num, pdf_file)
                precision.append(0.0)
            else:
                # both are 0, no table in the current page
                pass
            if DISPLAY_RESULTS:
                display_results(os.environ['DATAPATH'] + pdf_file, page_num, extracted_bbox, color=Color('blue'))
                display_results(os.environ['DATAPATH'] + pdf_file, page_num, gt_bbox, color=Color('red'))
    r = np.mean(recall) * 100
    p = np.mean(precision) * 100
    print "Per-page average Recall : {}%".format(r)
    print "Per-page average Precision : {}%".format(p)
    print "F1-measure : {}".format(2 * r * p / (r + p))
