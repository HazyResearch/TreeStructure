import numpy as np

from utils.bbox_utils import get_rectangles, compute_iou
from utils.lines_utils import reorder_lines, get_vertical_and_horizontal, extend_vertical_lines, \
    merge_vertical_lines, merge_horizontal_lines, extend_horizontal_lines
from pdf.pdf_parsers import parse_layout, parse_tree_structure
from pdf.pdf_utils import normalize_pdf, analyze_pages
from utils.display_utils import pdf_to_img
from ml.features import get_alignment_features, get_lines_features, get_mentions_within_bbox
from wand.color import Color
from wand.drawing import Drawing
from pdfminer.utils import Plane
import tabula
import json
from pdf.layout_utils import *

class TreeExtractor(object):
    """
    Object to extract tree structure from pdf files
    """

    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.elems = {}
        self.font_stats = {}
        self.lines_bboxes = []
        self.alignments_bboxes = []
        self.intersection_bboxes = []
        self.bboxes = []
        self.candidates = []
        self.features = []
        self.iou_thresh = 0.8
        self.scanned = False
        self.tree = {}
        self.html = ""

    def identify_scanned_page(self, boxes, page_bbox, page_width, page_height):
        plane = Plane(page_bbox)
        plane.extend(boxes)
        cid2obj = [set([i]) for i in xrange(len(boxes))] # initialize clusters
        obj2cid = range(len(boxes)) # default object map to cluster with its own index
        prev_clusters = obj2cid
        while(True):
            for i1, b1 in enumerate(boxes):
                for i2, b2 in enumerate(boxes):
                    box1 = b1.bbox
                    box2 = b2.bbox
                    if(box1[0]==box2[0] and box1[2]==box2[2] and round(box1[3])==round(box2[1])):
                        min_i = min(i1, i2)
                        max_i = max(i1, i2)
                        cid1 = obj2cid[min_i]
                        cid2 = obj2cid[max_i]
                        for obj_iter in cid2obj[cid2]:
                            cid2obj[cid1].add(obj_iter)
                            obj2cid[obj_iter] = cid1
                        cid2obj[cid2] = set()
            if(prev_clusters == obj2cid):
                break
            prev_clusters = obj2cid
        clusters = [[boxes[i] for i in cluster] for cluster in filter(bool, cid2obj)]
        if(len(clusters) == 1 and clusters[0][0].bbox[0]<-0.0 and clusters[0][0].bbox[1]<=0 and abs(clusters[0][0].bbox[2]-page_width)<=5 and abs(clusters[0][0].bbox[3]-page_height)<=5):
            return True
        return False

    def parse(self):
        is_scanned = False
        lin_seg_present = False
        for page_num, layout in enumerate(analyze_pages(self.pdf_file)):
            page_num += 1  # indexes start at 1
            elems, font_stat = normalize_pdf(layout, scaler=1)
            self.elems[page_num] = elems
            self.font_stats[page_num] = font_stat
            #code to detect if the page is scanned
            if(len(elems.segments)>0):
                lin_seg_present = True
            for fig in elems.figures:
                if(fig.bbox[0]<=0.0 and fig.bbox[1]<=0.0 and round(fig.bbox[2])==round(elems.layout.width) and round(fig.bbox[3])==round(elems.layout.height)):
                    is_scanned = True
            page_scanned = self.identify_scanned_page(elems.figures, elems.layout.bbox, elems.layout.width, elems.layout.height)
            if(page_scanned==True):
                is_scanned = True
        if(is_scanned==True or lin_seg_present==False): #doc is scanned if any page is scanned
            self.scanned = True    

    def is_scanned(self):
        if(len(self.elems) == 0):
           self.parse()
        return self.scanned

    def get_tables_page_num(self, page_num):
        page_boxes, _ = self.get_candidates_and_features_page_num(page_num)
        tables = page_boxes
        return tables

    def get_candidates_and_features_page_num(self, page_num):
        elems = self.elems[page_num]
        font_stat = self.font_stats[page_num]
        lines_bboxes = self.get_candidates_lines(page_num, elems)
        alignments_bboxes, alignment_features = self.get_candidates_alignments(page_num, elems)
        # print "Page Num: ", page_num, "Line bboxes: ", len(lines_bboxes), ", Alignment bboxes: ", len(alignments_bboxes)
        alignment_features += get_alignment_features(lines_bboxes, elems, font_stat)
        boxes = alignments_bboxes + lines_bboxes
        if len(boxes) == 0:
            return [], []
        lines_features = get_lines_features(boxes, elems)
        features = np.concatenate((np.array(alignment_features), np.array(lines_features)), axis=1)
        return boxes, features

    def get_candidates_lines(self, page_num, elems):
        page_width, page_height = int(elems.layout.width), int(elems.layout.height)
        lines = reorder_lines(elems.segments)
        vertical_lines, horizontal_lines = get_vertical_and_horizontal(lines)
        extended_vertical_lines = extend_vertical_lines(horizontal_lines)
        extended_horizontal_lines = extend_horizontal_lines(vertical_lines)
        vertical_lines = merge_vertical_lines(sorted(extended_vertical_lines + vertical_lines))
        horizontal_lines = merge_horizontal_lines(sorted(extended_horizontal_lines + horizontal_lines))
        rectangles = get_rectangles(sorted(vertical_lines), sorted(horizontal_lines))
        return [(page_num, page_width, page_height) + bbox for bbox in rectangles]

    def get_candidates_alignments(self, page_num, elems):
        page_width, page_height = int(elems.layout.width), int(elems.layout.height)
        font_stat = self.font_stats[page_num]
        try:
            nodes, features = parse_layout(elems, font_stat)
        except:
            nodes, features = [], []
        return [(page_num, page_width, page_height) + (node.y0, node.x0, node.y1, node.x1) for node in nodes], features

    def get_elems(self):
        return self.elems

    def get_font_stats(self):
        return self.font_stats

    def get_tree_structure(self, model):
        tables={}
        if(model is None):  #use heuristics to get tables
            for page_num in self.elems.keys():
                tables[page_num] = self.get_tables_page_num(page_num)
        else: #use ML to get tables
            for page_num in self.elems.keys():
                table_candidates, candidates_features = self.get_candidates_and_features_page_num(page_num)
                tables[page_num] = []
                if(len(candidates_features) != 0):
                    table_predictions = model.predict(candidates_features)
                    tables[page_num] = [table_candidates[i] for i in range(len(table_candidates)) if table_predictions[i]>0.5 ]
        ref_page_seen = False   #Manage References
        for page_num in self.elems.keys():
            self.tree[page_num], ref_page_seen = parse_tree_structure(self.elems[page_num], self.font_stats[page_num], page_num, ref_page_seen, tables[page_num])
            if len(self.tree[page_num]) > 0:
                self.tree[page_num]["table"] = tables[page_num]
        return self.tree

    def get_html_tree(self):
        self.html = "<html>"
        for page_num in self.elems.keys():
            page_html = "<div id="+str(page_num)+">"
            boxes = []
            for clust in self.tree[page_num]:
                for (pnum, pwidth, pheight, top, left, bottom, right) in self.tree[page_num][clust]:
                    boxes += [[clust.lower().replace(" ","_"), top, left, bottom, right]]
            boxes.sort(cmp=two_column_paper_order)
            for box in boxes:
                if(box[0] == "table"):
                    table = box[1:]
                    table_html = self.get_html_table(table, page_num)
                    page_html += table_html
                elif(box[0] == "figure"):
                    fig_str = [str(i) for i in box[1:]]
                    fig_html = "<figure bbox="+",".join(fig_str)+"></figure>"
                    page_html += fig_html
                else:
                    box_html = self.get_html_others(box[1:], page_num)
                    page_html += "<"+box[0]+">"+box_html+"</"+box[0]+">"
            page_html += "</div>"
            self.html += page_html
        self.html += "</html>"
        return self.html

    def get_html_others(self, box, page_num):
        node_html = ""
        elems = get_mentions_within_bbox(box, self.elems[page_num].mentions)
        elems.sort(cmp=reading_order)
        for elem in elems:
            node_html += elem.get_text()+" "
        return node_html

    def get_html_table(self, table, page_num):
        table_str = [str(i) for i in table]
        table_json = tabula.read_pdf(self.pdf_file, pages=page_num, area=table_str, output_format="json")
        table_html = ""
        if(len(table_json)>0):
            table_html = "<table>"
            for i, row in enumerate(table_json[0]["data"]):
                row_str = "<tr>"
                for j, column in enumerate(row):
                    row_str += "<td>"
                    row_str += column["text"]
                    row_str += "</td>"
                row_str += "</tr>"
                table_html += row_str
            table_html += "</table>"
        return table_html