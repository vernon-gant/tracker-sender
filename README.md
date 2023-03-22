# Automated Tracking Email Sender

This project is an extension of the automation of the Pux Button. It focuses on streamlining the process of sending emails with tracking numbers and links to customers after their orders have been dispatched.

## Workflow

1. Accept order number(s) from the console.
2. Fetch order details using a custom library (PrestaShopOrderClient).
3. Search email inbox for recent PDF attachments with specific names, indicating they are shipping labels.
4. Converts found label to image using Poppler.
5. Convert this image to text using Tesseract OCR engine.
6. Check match with the order based on details like first name, address, and postal code. Iterate 1-6 until label is found.
7. Identifiy the shipping company and extract the tracking number.
8. Sends the customer an email with their tracking number and link according to shipping company.

## Dependencies

- Poppler(pdf2image)
- Tesseract OCR (pytesseract)
- PrestaShopOrderClient (custom library)

## Usage

I created build and deploy scripts to make the deployment process as comfortable and efficient as possible for me. These scripts automate the following tasks:

1. Create a `requirements.txt` file containing the project's dependencies.
2. Check if the deployment directory exists, and clear or create it accordingly.
3. Copy project files to the deployment directory.
4. Create a virtual environment and install dependencies from the `requirements.txt` file.
5. Build an executable using PyInstaller.
6. Remove unnecessary files.

After deploying the script to a specific directory on my Windows computer, I added the script to the system PATH. Now, when I need to send a tracking email to a customer, I simply open the command prompt, type `tracker`, and the script starts executing.

