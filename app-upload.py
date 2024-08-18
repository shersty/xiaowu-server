import time
import io, os, sys
from flask_cors import CORS
from werkzeug.utils import secure_filename
from gevent import pywsgi

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append('{}'.format(ROOT_DIR))
sys.path.append('{}/third_party/Matcha-TTS'.format(ROOT_DIR))

import numpy as np
from flask import Flask, request, Response, redirect, url_for, jsonify
import torch
import torchaudio

from cosyvoice.cli.cosyvoice import CosyVoice
from cosyvoice.utils.file_utils import load_wav

cosyvoice = CosyVoice('pretrained_models/CosyVoice-300M-SFT')
UPLOAD_FOLDER = 'tmp/sounds'
ALLOWED_EXTENSIONS = set(['wav', 'txt'])

print(cosyvoice.list_avaliable_spks())

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route("/inference/stream", methods=['POST'])
def stream():
    question_data = request.get_json()
    tts_text = question_data.get('query')
    prompt_text = question_data.get('prompt_text')
    prompt_speech = load_wav(question_data.get('prompt_speech'), 16000)
    prompt_audio = (prompt_speech.numpy() * (2 ** 15)).astype(np.int16).tobytes()
    prompt_speech_16k = torch.from_numpy(np.array(np.frombuffer(prompt_audio, dtype=np.int16))).unsqueeze(dim=0)
    prompt_speech_16k = prompt_speech_16k.float() / (2 ** 15)
    if not tts_text:
        return {"error": "Query parameter 'query' is required"}, 400

    def generate_stream():
        for chunk in cosyvoice.stream(tts_text, prompt_text, prompt_speech_16k):
            float_data = chunk.numpy()
            byte_data = float_data.tobytes()
            print(f"len data: {len(byte_data)}")
            yield byte_data

    return Response(generate_stream(), mimetype="audio/pcm")


@app.route('/upload/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('upload_success', filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''


@app.route('/upload_success')
def upload_success():
    return '''
    <!doctype html>
    <title>上传成功</title>
    <h1>上传成功</h1>
    <a href="/upload/">继续上传</a>
    '''


@app.route('/api/upload/voice', methods=['POST'])
def upload_by_api():
    file = request.files['file']
    if file:
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': f'{file.filename} not valid.'})
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'success': True, 'message': f'File {filename} uploaded successfully.'})
    else:
        return jsonify({'success': False, 'message': 'No file found.'})


server = pywsgi.WSGIServer(('0.0.0.0', 6006), app)
server.serve_forever()

# if __name__ == "__main__":
#    app.run(host='0.0.0.0', port=6006,)
