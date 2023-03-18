import os
import csv
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import threading
import time


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists(app.config['OUTPUT_FOLDER']):
    os.makedirs(app.config['OUTPUT_FOLDER'])

progress = {
    'current': 0,
    'total': 0,
    'finished': False,
    'output_file': ''
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_seo_data(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.title.string if soup.title else ''
    meta_description = soup.find('meta', {'name': 'description'})
    meta_description = meta_description['content'] if meta_description else ''
    meta_keywords = soup.find('meta', {'name': 'keywords'})
    meta_keywords = meta_keywords['content'] if meta_keywords else ''

    headers = {}
    for i in range(1, 4):
        headers[f'H{i}'] = [header.text for header in soup.find_all(f'h{i}')]

    return {
        'url': url,
        'title': title,
        'meta_description': meta_description,
        'meta_keywords': meta_keywords,
        **headers
    }

def process_csv(input_file, output_file):
    global progress
    progress['finished'] = False

    with open(input_file, 'r', newline='', encoding='utf-8-sig') as infile:
        reader = csv.reader(infile)
        urls = [row[0] for row in reader]

    progress['total'] = len(urls)
    seo_data = []

    for index, url in enumerate(urls):
        try:
            data = get_seo_data(url)
            seo_data.append(data)
        except Exception as e:
            print(f"Error processing {url}: {e}")

        progress['current'] = index + 1

    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        fieldnames = ['url', 'title', 'meta_description', 'meta_keywords', 'H1', 'H2', 'H3']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in seo_data:
            writer.writerow(row)

    progress['finished'] = True
    progress['output_file'] = output_file

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    global progress

    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = file.filename
            input_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_file)

            output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'output_' + filename)

            threading.Thread(target=process_csv, args=(input_file, output_file)).start()

    return render_template('index.html', progress=progress)


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)


@app.route('/progress')
def get_progress():
    global progress
    return jsonify(progress)


if __name__ == "__main__":
    app.run(debug=True)
