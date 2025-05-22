import requests


def upload_jlc():
    """
    Submits a zip file to JLCPCB and retrieves the URL to the order page.
    """

    # API endpoint
    url = "https://cart.jlcpcb.com/api/overseas-shop-cart/v1/file/uploadGerber"

    file_path = "output.zip"
    files = {"gerberFile": open(file_path, "rb")}

    # Request
    data = {"calculationCostsType": "1"}

    headers = {
        "accept": "application/json, text/plain, */*",
        "cache-control": "no-cache",
    }

    # Exact data from chrome (doesn't work, just for reference)
    # headers = {
    #     "accept": "application/json, text/plain, /",
    #     "accept-language": "en-GB, en-US;q=0.9, en;q=0.8",
    #     "cache-control": "no-cache",
    #     "content-type": "multipart/form-data; boundary=----WebKitFormBoundarySvY28A6yVIy2sAAw",
    #     "pragma": "no-cache",
    #     "priority": "u=1, i",
    #     "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    #     "sec-ch-ua-mobile": "?0",
    #     "sec-ch-ua-platform": '"Windows"',
    #     "sec-fetch-dest": "empty",
    #     "sec-fetch-mode": "cors",
    #     "sec-fetch-site": "same-origin",
    #     "secretkey": "30626637303034332d366337642d346233382d386133392d353336616232663931383035",
    #     "x-xsrf-token": "726726cf-24c3-4859-ac5b-0bed9f24ed4d",
    # }

    # "referrer": "https://cart.jlcpcb.com/quote?spm=Jlcpcb.Homepage.1006",
    # "referrerPolicy": "strict-origin-when-cross-origin",
    # "body": '------WebKitFormBoundarySvY28A6yVIy2sAAw\r\nContent-Disposition: form-data; name="gerberFile"; filename="output (37).zip"\r\nContent-Type: application/x-zip-compressed\r\n\r\n\r\n------WebKitFormBoundarySvY28A6yVIy2sAAw\r\nContent-Disposition: form-data; name="calculationCostsType"\r\n\r\n1\r\n------WebKitFormBoundarySvY28A6yVIy2sAAw--\r\n',
    # "method": "POST",
    # "mode": "cors",
    # "credentials": "include"

    response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code == 200:
        print("🟢 Successfully uploaded to JLCPCB")
        json_response = response.json()
        data = json_response.get("data")
        file_id = data.get("fileId")

        jlc_order_url = "https://cart.jlcpcb.com/quote?homeUploadNum=" + file_id
        if file_id:
            print("🟢 Access at:", jlc_order_url)
        return jlc_order_url
    else:
        print("🔴 Failed to upload to JLCPCB")
