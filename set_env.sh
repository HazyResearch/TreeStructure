export TREE_HOME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export TABLE_EXTRACTION_HOME="$TREE_HOME/table-extraction/"
export TESSERACT_EXTRACTION_HOME="$TREE_HOME/table-extraction/tesseract/"
export PYTHONPATH="$PYTHONPATH:$TREE_HOME:$TABLE_EXTRACTION_HOME"
export PYTHONPATH=“$PYTHONPATH:$TREE_HOME:$TESSERACT_EXTRACTION_HOME”
export DATAPATH="$TREE_HOME/data/test-scanned/"
export MLPATH="$TREE_HOME/data/test-scanned/"
