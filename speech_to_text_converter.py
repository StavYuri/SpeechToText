import io
import os
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from google.oauth2 import service_account
from pydub import AudioSegment
from google.cloud import storage
from email_sender import EmailSender
import json


class SpeechToTextConverter:
    speech_client = None
    storage_client = None

    def __init__(self, credentials_path):
        self.set_up_credentials(credentials_path)

    def set_up_credentials(self, credentials_path):
        my_credentials = service_account.Credentials.from_service_account_file(credentials_path)
        self.speech_client = speech.SpeechClient(credentials=my_credentials)
        self.storage_client = storage.Client.from_service_account_json(credentials_path)

    def convert_to_text_short_file(self):
        # The name of the audio file to transcribe
        file_name = os.path.join(os.path.dirname(__file__), 'resources', 'audio.flac')

        # Loads the audio into memory
        with io.open(file_name, 'rb') as audio_file:
            content = audio_file.read()
            audio = types.RecognitionAudio(content=content)

        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
            sample_rate_hertz=44100,
            language_code='fr-CA')

        # Detects speech in the audio file
        response = self.speech_client.recognize(config, audio)

        for result in response.results:
            print('Transcript: {}'.format(result.alternatives[0].transcript))

    def convert_to_text_long_file(self):
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
            sample_rate_hertz=44100,
            language_code='fr-CA')

        storage_uri = "gs://your_bucket_name/audio.flac"
        audio = {"uri": storage_uri}
        operation = self.speech_client.long_running_recognize(config, audio)
        response = operation.result()

        for result in response.results:
            print('Transcript: {}'.format(result.alternatives[0].transcript))

    def watch_bucket(self, bucket_name):
        # All files in bucket
        blobs = self.storage_client.list_blobs(bucket_name)

        # info.js file contains information about processed files
        bucket = self.storage_client.get_bucket(bucket_name)
        info_blob = bucket.blob('info.json')
        info_blob_content = info_blob.download_as_string().decode('utf8')
        info_blob_content_as_json = json.loads(info_blob_content)
        processed_files_count = len(info_blob_content_as_json)

        text_result = ""

        for blob in blobs:
            # We have to skip info file
            if blob.name != "info.json":
                was_processed = self.file_was_processed(blob, info_blob_content_as_json)
                if not was_processed:

                    # Save to local file from google bucket
                    local_file_path = self.download_file_from_bucket(blob.name, bucket.name, "temp.m4a")

                    # Convert local file from .m4a to .flac
                    converted_file = self.convert_audio_file(local_file_path, "flac", blob.name.split('.')[0])

                    # Save .flac file to bucket
                    converted_file_as_blob = self.upload_file_to_bucket(converted_file, bucket.name)

                    # Process file through google speech to text api
                    text_result = self.process_file(converted_file_as_blob, info_blob_content_as_json, "fr-CA")

                    # Send email with audio file content
                    sender = EmailSender("your_email@hotmail.com")
                    sender.send_email(text_result, "Result from file: {} ".format(blob.name))

        # Delete old info file and create new one
        if processed_files_count < len(info_blob_content_as_json):
            self.update_info_file(info_blob, bucket, info_blob_content_as_json)

    def file_was_processed(self, file_to_validate, processed_files_info):
        already_processed = False

        if len(processed_files_info) > 0:
            for fileInfo in processed_files_info:
                # Checking only file name and ignore extension
                if fileInfo["fileName"].split('.')[0] == file_to_validate.name.split('.')[0]:
                    already_processed = True
                    break

        return already_processed

    def process_file(self, file, processed_files_info, lang):
        result = self.convert_to_text_long_file(file.bucket.name, file.name, lang)
        processed_files_info.append({"fileName": "{}".format(file.name), "processed": "{}".format(file.time_created)})
        return result

    def update_info_file(self, current_info_file, bucket, new_info_file_content):
        current_info_file.delete()
        new_blob = bucket.blob('info.json')
        new_blob.upload_from_string(json.dumps(new_info_file_content))

    def convert_to_text_long_file(self, bucket_name, file_name, lang):
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
            sample_rate_hertz=44100,
            language_code=lang)

        storage_uri = "gs://{0}/{1}".format(bucket_name, file_name)
        audio = {"uri": storage_uri}
        operation = self.speech_client.long_running_recognize(config, audio)
        response = operation.result()
        text = []

        for result in response.results:
            text.append(result.alternatives[0].transcript)

        return "\n".join(text)

    def convert_audio_file(self, file_to_convert, to_format, converted_file_name):
        AudioSegment.from_file(file_to_convert).export(converted_file_name, format=to_format)

        return converted_file_name

    def download_file_from_bucket(self, file_name, bucket_name, file_destination):
        bucket = self.storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_name)
        blob.download_to_filename(file_destination)

        return file_destination

    def upload_file_to_bucket(self, file_to_upload_path, bucket_name):
        bucket = self.storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_to_upload_path)
        blob.upload_from_filename(file_to_upload_path)

        return blob



