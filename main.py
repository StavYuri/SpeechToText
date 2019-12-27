from speech_to_text_converter import SpeechToTextConverter
import schedule
import time


def main():

    converter = SpeechToTextConverter("path_to_your_credential_json_file")

    def execute_job():
        converter.watch_bucket("your_bucket_name")

    schedule.every(10).minutes.do(execute_job)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
