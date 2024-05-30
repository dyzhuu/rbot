import base64
import os


def write_prompt_file():
    # Example base64 string
    base64_string = os.getenv('SETUP_PROMPT')

    # Decode the base64 string
    decoded_data = base64.b64decode(base64_string).decode('utf-8')

    # Specify the output file path
    output_file_path = os.path.join("prompt.txt")

    with open(output_file_path, "w") as file:
        file.write(decoded_data)
    print(f"Data has been written to {output_file_path}")
