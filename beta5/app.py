import openai
import os
import requests
import uuid
from flask import Flask, request, jsonify, send_file, render_template
from elevenlabs import clone, generate

# Add your OpenAI API key
OPENAI_API_KEY = "your-openai-api-key"
openai.api_key = OPENAI_API_KEY
# Add your ElevenLabs API key
from elevenlabs import set_api_key
set_api_key("e44cad73fbed6ff8a19f55d9b8224998")
# Choose your voice files for ElevenLabs
VOICE_NAME = "Alex"
VOICE_DESCRIPTION = "An old American male voice with a slight hoarseness in his throat. Perfect for news"

# Get all sample files in the 'samples/' directory
VOICE_FILES = [f"uploads/{name}" for name in os.listdir('uploads/') if os.path.isfile(os.path.join('uploads/', name))]

# Clone a voice with ElevenLabs
VOICE = clone(
    name=VOICE_NAME,
    description=VOICE_DESCRIPTION,
    files=VOICE_FILES,
)

app = Flask(__name__)

def transcribe_audio(filename: str) -> str:
    """Transcribe audio to text.

    :param filename: The path to an audio file.
    :returns: The transcribed text of the file.
    :rtype: str

    """
    with open(filename, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript.text

def generate_reply(conversation: list) -> str:
    """Generate a ChatGPT response.

    :param conversation: A list of previous user and assistant messages.
    :returns: The ChatGPT response.
    :rtype: str

    """
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=[
            {"role": "system", "content": "You are a helpful assistant."},
        ] + conversation
    )
    return response["choices"][0]["message"]["content"]

def generate_audio(text: str, output_path: str = "") -> str:
    """Converts text to audio using ElevenLabs and saves the audio file.

    :param text: The text to convert to audio.
    :type text : str
    :param output_path: The location to save the finished audio file.
    :type output_path: str
    :returns: The output path for the successfully saved file.
    :rtype: str

    """
    audio = generate(text=text, voice=VOICE)
    with open(output_path, "wb") as output:
        output.write(audio)
    return output_path

@app.route('/')
def index():
    """Render the index page."""
    return render_template('index.html', voice=VOICE_NAME)

@app.route('/upload_sample', methods=['POST'])
def upload_sample():
    """Upload a voice sample to be used for cloning."""
    if 'file' not in request.files:
        return 'No file found', 400
    file = request.files['file']
    # Create a new filename based on the number of existing samples
    num_samples = len([name for name in os.listdir('samples/') if os.path.isfile(os.path.join('samples/', name))])
    sample_file = f"sample_{num_samples + 1}.mp3"
    sample_path = f"samples/{sample_file}"
    os.makedirs(os.path.dirname(sample_path), exist_ok=True)
    file.save(sample_path)
    return jsonify({'message': 'File uploaded successfully', 'filename': sample_file})

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Transcribe the given audio to text using Whisper."""
    if 'file' not in request.files:
        return 'No file found', 400
    file = request.files['file']
    recording_file = f"{uuid.uuid4()}.wav"
    recording_path = f"uploads/{recording_file}"
    os.makedirs(os.path.dirname(recording_path), exist_ok=True)
    file.save(recording_path)
    transcription = transcribe_audio(recording_path)
    return jsonify({'text': transcription})

@app.route('/ask', methods=['POST'])
def ask():
    """Generate a ChatGPT response from the given conversation, then convert it to audio using ElevenLabs."""
    conversation = request.get_json(force=True).get("conversation", "")
    reply = generate_reply(conversation)
    reply_file = f"{uuid.uuid4()}.mp3"
    reply_path = f"outputs/{reply_file}"
    os.makedirs(os.path.dirname(reply_path), exist_ok=True)
    generate_audio(reply, output_path=reply_path)
    return jsonify({'text': reply, 'audio': f"/listen/{reply_file}"})

@app.route('/listen/<filename>')
def listen(filename):
    """Return the audio file located at the given filename."""
    return send_file(f"outputs/{filename}", mimetype="audio/mp3", as_attachment=False)

if __name__ == '__main__':
    app.run()
