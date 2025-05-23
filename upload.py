import requests

file_path = "output.zip"


def setup():
    """
    Prepares the files for upload.
    """

    # Check if the zip file exists
    try:
        with open("output.zip", "rb") as _:
            pass
    except FileNotFoundError:
        print("🔴 output.zip not found. Please run the script to generate it.")
        return


def upload_jlc():
    """
    Submits a zip file to JLCPCB and retrieves the URL to the order page.
    """
    setup()

    # API endpoint
    url = "https://cart.jlcpcb.com/api/overseas-shop-cart/v1/file/uploadGerber"

    # Form data
    data = {"calculationCostsType": "1"}

    headers = {
        "accept": "application/json, text/plain, */*",
        "cache-control": "no-cache",
    }

    global file_path
    files = {"gerberFile": open(file_path, "rb")}

    """
    Reference headers:

        headers = {
            "accept": "application/json, text/plain, /",
            "accept-language": "en-GB, en-US;q=0.9, en;q=0.8",
            "cache-control": "no-cache",
            "content-type": "multipart/form-data; boundary=----WebKitFormBoundarySvY28A6yVIy2sAAw",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "secretkey": "30626637303034332d366337642d346233382d386133392d353336616232663931383035",
            "x-xsrf-token": "726726cf-24c3-4859-ac5b-0bed9f24ed4d",
        }

    Properties:

        "referrer": "https://cart.jlcpcb.com/quote?spm=Jlcpcb.Homepage.1006",
        "referrerPolicy": "strict-origin-when-cross-origin",
        "body": '------WebKitFormBoundarySvY28A6yVIy2sAAw\r\nContent-Disposition: form-data; name="gerberFile"; filename="output (37).zip"\r\nContent-Type: application/x-zip-compressed\r\n\r\n\r\n------WebKitFormBoundarySvY28A6yVIy2sAAw\r\nContent-Disposition: form-data; name="calculationCostsType"\r\n\r\n1\r\n------WebKitFormBoundarySvY28A6yVIy2sAAw--\r\n',
        "method": "POST",
        "mode": "cors",
        "credentials": "include"

    Response:

        {
            "code": 200,
            "data": {
                "fileId": "cc39a7d04a7743938f4ce34de9270b1b",
                "fileName": "output (48).zip",
                "calculationCostsType": 1,
                "result": "success",
                "resultStatus": null,
                "s3SignatureResponse": {
                "local": true,
                "uploadFileToS3Url": null,
                "httpStatusCode": null,
                "signature": null,
                "uploadBySignatureRequest": null
                },
                "fileSystemAccessId": "8614393686272851968",
                "uid": null
            },
            "message": null
        }

    """

    response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code == 200:
        print("🟢 Successfully uploaded to JLCPCB")
        json_response = response.json()
        data = json_response.get("data")
        file_id = data.get("fileId")

        order_url = "https://cart.jlcpcb.com/quote?homeUploadNum=" + file_id
        if file_id:
            print("🟢 Access at:", order_url)
        return order_url
    else:
        print("🔴 Failed to upload to JLCPCB")


def upload_euro():
    """
    Submits a zip file to Eurocircuits and retrieves the URL to the order page.
    """
    setup()

    # API endpoint
    url = (
        "https://www.eurocircuits.com/wp-json/eurocircuits/v1/calculation-upload-file/"
    )

    # Form data
    data = {"data_type": "pcb"}

    headers = {
        "accept": "application/json, text/plain, */*",
        "cache-control": "no-cache",
    }

    global file_path
    files = {"file": open(file_path, "rb")}

    """
    Reference headers:

        headers = {
            "accept": "application/json",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "content-type": "multipart/form-data; boundary=----WebKitFormBoundaryf6ekasTaY2DqAx5N",
            "priority": "u=1, i",
            "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest",
        }

    Properties:

        "referrer": "https://www.eurocircuits.com/",
        "referrerPolicy": "no-referrer-when-downgrade",
        "method": "POST",
        "mode": "cors",
        "credentials": "include"

    Response:

        {
            "success": true,
            "message": "File uploaded successfully and sent to external service.",
            "redirect_url": "https://be.eurocircuits.com/shop/assembly/configurepcb.aspx?sessionid=d9bfe4b5-dc9a-4e9b-80cf-3b1e747c971f&from=wp&type=PCB&filename=output-37.zip"
        }

    """

    response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code == 200:
        print("🟢 Successfully uploaded to Eurocircuits")
        print(response.text)
        json_response = response.json()
        print(json_response)
        order_url = json_response.get("redirect_url")
        if order_url:
            print("🟢 Access at:", order_url)
        return order_url
    else:
        print("🔴 Failed to upload to Eurocircuits")
        print(response)
        print(response.text)
