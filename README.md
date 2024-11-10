# GenAI-Stage-1-Task
## Installation
First clone my repository
```
git clone https://github.com/PeacockBen/GenAI-Stage-1-Task.git
cd your-repo-name
```
Next, create a virtual environment, and activate
```
python -m venv venv
venv\Scripts\activate
```
Install necessary packages:
```
pip install --upgrade pip
pip install paddlepaddle
pip install paddleocr
pip install PyMuPDF
pip install numpy
pip install Pillow
pip install googletrans==4.0.0rc1
pip install fuzzywuzzy[speedup]
```
## Usage
Ensure all PDFs are placed in a folder named 'input_pdfs' in the project directory 
Run the script:
```
python main.py
```
Extracted information will  be saved in json file 'data.json'


