from ctypes import *

strata_client_lib = CDLL('libstrata_client.so')

post_signature = strata_client_lib.post_signature
post_signature.argtypes = [ c_char_p, c_char_p, c_char_p, c_char_p ]
post_signature.restype = c_char_p

send_report_to_new_case = strata_client_lib.send_report_to_new_case
send_report_to_new_case.argtypes = [ c_char_p, c_char_p, c_char_p, c_char_p, c_char_p, c_char_p, c_char_p, c_char_p, c_char_p ]
send_report_to_new_case.restype = c_char_p

send_report_to_existing_case = strata_client_lib.send_report_to_existing_case
send_report_to_existing_case.argtypes = [ c_char_p, c_char_p, c_char_p, c_char_p, c_char_p ]
send_report_to_existing_case.restype = c_char_p

strata_client_strerror = strata_client_lib.strata_client_strerror
strata_client_strerror.argtypes = []
strata_client_strerror.restype = c_char_p


