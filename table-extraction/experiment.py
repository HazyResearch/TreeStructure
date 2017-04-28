'''
Created on Oct 14, 2016

@author: xiao
'''
from parse import process_pdf, parse_args
from argparse import Namespace
from pdfminer.layout import LTTextLine
import codecs
import csv
import os

extractions = []

def get_gold_dict(filename, doc_on=True, part_on=True, val_on=True, attrib=None, docs=None):
    with codecs.open(filename, encoding="utf-8") as csvfile:
        gold_reader = csv.reader(csvfile)
        gold_dict = set()
        for row in gold_reader:
            (doc, part, val, attr) = row
            if docs is None or doc.upper() in docs:
                if attrib and attr != attrib:
                    continue
                else:
                    key = []
                    if doc_on:  key.append(doc.upper())
                    if part_on: key.append(part.upper())
                    if val_on:  key.append(val.upper())
                    gold_dict.add(tuple(key))
    return gold_dict

def qualified_row(text):
    text = text.lower()
    return 'hfe' in text or 'dc gain' in text or 'dc current gain' in text

def process_row(row, location = None, debug = False, extractable = lambda x: False):
    '''
    Going over the mentions in a row, either print the contents for debugging or use a 
    matcher function to decide whether include this row in the extraction output
    '''
    if debug:
        print location, '=' * 80
        print str(row)[:50]
    for y_coord, row_contents in sorted(row.items()):
        if debug: print '=' * 40, y_coord
        row_texts = []
        for mention in sorted(set(row_contents), key=lambda m:m.x0):
            text = mention.clean_text
            if extractable(text):
                return True
            row_texts.append(text)
        if debug: print '\t'.join(row_texts)
    return False

def process_elem(filename, page_num, regions, debug = False):
    if debug: print '+Page', page_num
    for e in regions:
        if not e.is_table(): continue
        grid = e.get_grid()
        print grid.to_html()
        raw_input('')
        break
        
        if debug: print '++Table', e.bbox[:2], str(e)[:50]
        
        prev = None
        for row in grid.get_normalized_grid():
            # Some rows are duplicated for layout
            if prev == row: continue
            valid_row = process_row(row, filename, extractable=qualified_row)
            if valid_row: 
                extractions.append(row)
                location = filename + " page " + str(page_num)
                process_row(row, location = location, debug = True)
                raw_input()
            
            prev = row
        
#         for e in e.elems:
#             if not isinstance(e, LTTextLine): continue
#             text = e.clean_text.lower()
#             print text
        if debug: print '+'*80, '\n', '+'*80
#         raw_input()
    pass

def get_html_tables():
    args = Namespace()
    args.verbose = False
    args.debug = False
    args.page = 0
    root = 'test/'
    pdfs = os.listdir(root)
#     print '\n'.join(pdfs)
    pdfs = pdfs[3:4]
#     pdfs.sort()
    for i, f in enumerate(pdfs):
        if not f.lower().endswith('.pdf'): continue
        args.filename = root + f
        for page_num, nodes in enumerate(process_pdf(args)):
            for node in nodes:
                if node.is_table():
                    grid = node.get_grid()
                    yield f, page_num, grid.to_html()
    

if __name__ == '__main__':
    args = Namespace()
    args.verbose = False
    args.debug = False
    args.page = 0
    root = 'test/'
    pdfs = os.listdir(root)
    for i, f in enumerate(pdfs):
        if not f.lower().endswith('.pdf'): continue
        args.filename = root + f
        
        process_pdf(args, process_elem)
    