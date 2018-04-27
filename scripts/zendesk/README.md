# Data Extraction and Reporting for Zendesk

## Requirements
Follow installation instructions from [zdesk](https://github.com/fprimex/zdesk).
The following environment variables are needed:
* `ZENDESK_URL` - Your zendesk url. Typically it is `https://<yoursite>.zendesk.com`
* `ZENDESK_USERNAME` - The username you use to login to zendesk.
* `ZENDESK_TOKEN` - API token. You will need to create this in your Zendesk profile.
* `ZENDESK_OUTPUT_PATH` - where you want to output the files.

## Usage
* To do a full run: `python main.py run`.
* To execute individual parts, run `python main.py` and use the exposed options.