import requests
from requests import Response

BASE_URL = 'https://uwebasr.zcu.cz/api/v1/CLARIN_ASR/CZ'


# curl request example
# curl -X POST -N --data-binary @record_1651872811.766579.wav 'https://uwebasr.zcu.cz/api/v1/CLARIN_ASR/CZ?format=plaintext'


def convert(file_name, output_format='plaintext') -> Response:
    """

    :param file_name:
    :param output_format: plaintext|json
    :return:
    """
    with open(file_name, 'rb') as file_reader:
        res = post_binary_data(file_reader, output_format)
        res.raise_for_status()
        return res


def post_binary_data(file, response_format) -> Response:
    # data = 'test data'
    res = requests.post(url=BASE_URL,
                        data=file,
                        params={"format": response_format})
    print('post_binary_data to ' + BASE_URL + ' -> ' + res)
    return res


# res = convert('../record_1651913884.758266.wav', 'json')
# print(res.json())
