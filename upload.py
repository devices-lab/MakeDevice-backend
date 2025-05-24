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
        print(response)
        print(response.text)


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
        json_response = response.json()
        order_url = json_response.get("redirect_url")
        if order_url:
            print("🟢 Access at:", order_url)
        return order_url
    else:
        print("🔴 Failed to upload to Eurocircuits")
        print(response)
        print(response.text)


def upload_pcbway():
    """
    Submits a zip file to PCBWay and retrieves the URL to the order page.
    """

    # FIX: This this one doesn't work, I didn't spend long looking into it, PCBWay
    # lets us upload files via POST request and responds with a URL to that uploaded
    # file, but I don't think there's a way to give a client a URL that takes them to
    # an order page with that file loaded.

    setup()

    # API endpoint
    url = "https://www.pcbway.com/common/upfile/"

    # Form data
    data = {"name": "output.zip"}
    data = {"uptype": "gerberfile"}

    headers = {
        "accept": "application/json, text/plain, */*",
        "cache-control": "no-cache",
    }

    """
    Reference headers:

        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "content-type": "multipart/form-data; boundary=----WebKitFormBoundaryIOCavAfwzkzo5BXv",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }

    Properties:

        "referrer": "https://www.pcbway.com/QuickOrderOnline.aspx",
        "referrerPolicy": "strict-origin-when-cross-origin",
        "body": "------WebKitFormBoundaryIOCavAfwzkzo5BXv\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\noutput (69).zip\r\n------WebKitFormBoundaryIOCavAfwzkzo5BXv\r\nContent-Disposition: form-data; name=\"uptype\"\r\n\r\ngerberfile\r\n------WebKitFormBoundaryIOCavAfwzkzo5BXv\r\nContent-Disposition: form-data; name=\"file\"; filename=\"output (69).zip\"\r\nContent-Type: application/x-zip-compressed\r\n\r\n\r\n------WebKitFormBoundaryIOCavAfwzkzo5BXv--\r\n",
        "method": "POST",
        "mode": "cors",
        "credentials": "include"

    Response:

        {
            "url": "https://pcbwayfile.s3.us-west-2.amazonaws.com/gerber/25/05/24/075614912d64f7878f75c46fc82e29625b99f7c246670.zip",
            "title": "",
            "original": "output (69).zip",
            "state": "SUCCESS"
        }

    """

    global file_path
    files = {"file": open(file_path, "rb")}

    response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code == 200:
        print("🟢 Successfully uploaded to PCBWay")
        json_response = response.json()
        file_url = json_response.get("url")
        # FIX: Do another request to get the order URL
        order_url = None
        if order_url:
            print("🟢 Access at:", order_url)
        return order_url
    else:
        print("🔴 Failed to upload to PCBWay")
        print(response)
        print(response.text)


def upload_aisler():
    """
    Submits a zip file to Aisler and retrieves the URL to the order page.
    """
    setup()

    # First have to do a GET request to get a new project ID/upload URL
    upload_url = None
    order_url = None
    url = "https://aisler.net/p/new.json?locale=en"
    """
        Response:
        
            {
                "project_url": "https://aisler.net/p/BFPSKZOJ?locale=en",
                "project_id": "BFPSKZOJ",
                "upload_url": "https://aisler.net/p/BFPSKZOJ/uploads.json?locale=en"
            }

    """
    response = requests.get(url)
    if response.status_code == 201:  # Aisler uses proper HTTP status codes
        print("🟢 Successfully retrieved new project ID from Aisler")
        json_response = response.json()
        upload_url = json_response.get("upload_url")
        order_url = json_response.get("project_url")
    else:
        print("🔴 Failed to retrieve new project ID from Aisler")
        print(response)
        print(response.text)
        return

    # Now regular POST request process

    # API endpoint
    url = upload_url

    headers = {
        "accept": "*/*",
        "cache-control": "no-cache",
    }

    """
    Reference headers:

        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "content-type": "multipart/form-data; boundary=----WebKitFormBoundaryuwsL1kp29leLKd8M",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }

    Properties:
            
        "referrer": "https://aisler.net/en",
        "referrerPolicy": "strict-origin-when-cross-origin",
        "method": "POST",
        "mode": "cors",
        "credentials": "include"

    Response:

        201 Created
    """

    # Aisler has a weird form, couldn't see the content-disposition in chrome network tab
    # so used a packet inspector to find out "upload[file]" and octet-stream (set up SSL
    # decryption, then "Follow HTTP/2 Stream" to see the request)
    global file_path
    files = {
        "upload[file]": (
            "output.zip",
            open(file_path, "rb"),
            "application/octet-stream",
        )
    }
    response = requests.post(url, headers=headers, files=files)

    if response.status_code == 201:
        print("🟢 Successfully uploaded to Aisler")
        print("🟢 Access at:", order_url)
        return order_url
    else:
        print("🔴 Failed to upload to Aisler")
        print(response)
        print(response.text)
