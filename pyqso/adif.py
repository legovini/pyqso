#!/usr/bin/env python 
# File: adif.py

#    Copyright (C) 2012 Christian Jacobs.

#    This file is part of PyQSO.

#    PyQSO is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    PyQSO is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PyQSO.  If not, see <http://www.gnu.org/licenses/>.

import re
import logging
import unittest
from datetime import datetime
import calendar

# All the possible field names and their associated data types 
# from the ADIF specification (version 3.0.2)
AVAILABLE_FIELD_NAMES_TYPES = {"CALL": "S", 
                              "QSO_DATE": "D",
                              "TIME_ON": "T",
                              "FREQ": "N",
                              "BAND": "E",
                              "MODE": "E",
                              "RST_SENT": "S",
                              "RST_RCVD": "S"}

AVAILABLE_FIELD_NAMES_ORDERED = ["CALL", "QSO_DATE", "TIME_ON", "FREQ", "BAND", "MODE", "RST_SENT", "RST_RCVD"]

# A: AwardList
# B: Boolean
# N: Number
# S: String
# I: International string
# D: Date
# T: Time
# M: Multi-line string
# G: Multi-line international string
# L: Location
DATA_TYPES = ["A", "B", "N", "S", "I", "D", "T", "M", "G", "L", "E"]

ADIF_VERSION = "3.0.2"

class ADIF:
   
   def __init__(self):
      # Class for I/O of files using the Amateur Data Interchange Format (ADIF).
      logging.debug("New ADIF instance created!")
      
   def read(self, path):
      
      logging.debug("Reading in ADIF file with path: %s." % path)
      
      try:
         f = open(path, 'r')
         text = f.read()
         f.close() # Close the file, otherwise "bad things" might happen!
      except IOError as e:
         logging.error("I/O error %d: %s" % (e.errno, e.strerror))
         raise
      except:
         logging.error("Unknown error occurred when reading the ADIF file.")
         raise
      
      records = self.parse_adi(text)
         
      if(records == []):
         logging.warning("No records found in the file. Empty file or wrong file type?")
         
      return records
      
   def parse_adi(self, text):
      records = []

      # Separate the text at the <eor> or <eoh> markers.
      tokens = re.split('(<eor>|<eoh>)', text, flags=re.IGNORECASE)
      tokens.pop() # Anything after the final <eor> marker should be ignored.
      
      # The header might tell us the number of records, but let's not assume
      # this and simply ignore it instead (if it exists).
      if(re.search('<eoh>', text, flags=re.IGNORECASE) is not None):
         # There is a header present, so let's ignore everything
         # up to and including the <eoh> marker. Note that
         # re.search has been used here to handle any case sensitivity.
         # Previously we were checking for <eoh>. <EOH> is also valid
         # but wasn't been detected before.
         while len(tokens) > 0:
            t = tokens.pop(0)
            if(re.match('<eoh>', t, flags=re.IGNORECASE) is not None):
               break
            
      n_eor = 0 
      n_record = 0
      records = []
      for t in tokens:
         if(re.match('<eor>', t, flags=re.IGNORECASE) is not None):
            n_eor = n_eor + 1
            continue
         else:
            n_record = n_record + 1
            # Each record will have field names and corresponding
            # data entries. Store this in a dictionary.
            # Note: This is based on the code written by OK4BX.
            # (http://web.bxhome.org/blog/ok4bx/2012/05/adif-parser-python)
            fields_and_data_dictionary = {}
            fields_and_data = re.findall('<(.*?):(\d*).*?>([^<\t\n\r\f\v\Z]+)', t)  
            for fd in fields_and_data:
               # Let's force all field names to be in upper case.
               # This will help us later when comparing the field names
               # against the available field names in the ADIF specification.
               fields_and_data_dictionary[fd[0].upper()] = fd[2][:int(fd[1])]
            records.append(fields_and_data_dictionary)
      
      assert n_eor == n_record
      
      return records

      
   def write(self, records, path):
      f = open(path, 'w') # Open file for writing
      
      # First write a header containing program version, number of records, etc.
      dt = datetime.now()
      
      f.write('''Amateur radio log file. Generated on %s. Contains %d record(s). 
      
<adif_ver:5>%s
<programid:5>PyQSO
<programversion:8>0.1a.dev

<eoh>\n''' % (dt, len(records), ADIF_VERSION))
      
      # Then write each log to the file.
      for r in records:
         for field_name in AVAILABLE_FIELD_NAMES_ORDERED:
            if( (r[field_name] != "NULL") and (r[field_name] != "") ):
               f.write("<%s:%d>%s\n" % (field_name.lower(), len(r[field_name]), r[field_name]))
         f.write("<eor>\n")

      f.close()


   def is_valid(self, field_name, data, data_type):
      ''' Validate the fields with respect to the ADIF specification '''
      
      # Allow an empty string, in case the user doesn't want
      # to fill in this field.
      if(data == ""):
         return True

      if(data_type == "N"):
         # Allow a decimal point before and/or after any numbers,
         # but don't allow a decimal point on its own.
         m = re.match(r"-?(([0-9]+\.?[0-9]*)|([0-9]*\.?[0-9]+))", data)
         if(m is None):
            # Did not match anything.
            return False
         else:
            # Make sure we match the whole string,
            # otherwise there may be an invalid character after the match. 
            return (m.group(0) == data)
      
      elif(data_type == "B"):
         # Boolean
         m = re.match(r"(Y|N)", data)
         if(m is None):
            return False
         else:
            return (m.group(0) == data)

      elif(data_type == "D"):
         # Date
         pattern = re.compile(r"([0-9]{4})")
         m_year = pattern.match(data, 0)
         if((m_year is None) or (int(m_year.group(0)) < 1930)):
            # Did not match anything.
            return False
         else:
            pattern = re.compile(r"([0-9]{2})")
            m_month = pattern.match(data, 4)
            if((m_month is None) or int(m_month.group(0)) > 12 or int(m_month.group(0)) < 1):
               # Did not match anything.
               return False
            else:
               pattern = re.compile(r"([0-9]{2})")
               m_day = pattern.match(data, 6)
               days_in_month = calendar.monthrange(int(m_year.group(0)), int(m_month.group(0)))
               if((m_day is None) or int(m_day.group(0)) > days_in_month[1] or int(m_day.group(0)) < 1):
                  # Did not match anything.
                  return False
               else:
                  # Make sure we match the whole string,
                  # otherwise there may be an invalid character after the match. 
                  return (len(data) == 8)

      elif(data_type == "T"):
         # Time
         pattern = re.compile(r"([0-9]{2})")
         m_hour = pattern.match(data, 0)
         if((m_hour is None) or (int(m_hour.group(0)) < 0) or (int(m_hour.group(0)) > 23)):
            # Did not match anything.
            return False
         else:
            pattern = re.compile(r"([0-9]{2})")
            m_minutes = pattern.match(data, 2)
            if((m_minutes is None) or int(m_minutes.group(0)) < 0 or int(m_minutes.group(0)) > 59):
               # Did not match anything.
               return False
            else:
               if(len(data) == 4):
                  # HHMM format
                  return True
               pattern = re.compile(r"([0-9]{2})")
               m_seconds = pattern.match(data, 4)
               if((m_seconds is None) or int(m_seconds.group(0)) < 0 or int(m_seconds.group(0)) > 59):
                  # Did not match anything.
                  return False
               else:
                  # Make sure we match the whole string,
                  # otherwise there may be an invalid character after the match. 
                  return (len(data) == 6) # HHMMSS format

      #FIXME: Need to make sure that the "S" and "M" data types accept ASCII-only characters
      # in the range 32-126 inclusive.
      elif(data_type == "S"):
         # String
         m = re.match(r"(.+)", data)
         if(m is None):
            return False
         else:
            return (m.group(0) == data)

      elif(data_type == "I"):
         # IntlString
         m = re.match(ur"(.+)", data, re.UNICODE)
         if(m is None):
            return False
         else:
            return (m.group(0) == data)

      elif(data_type == "G"):
         # IntlMultilineString
         m = re.match(ur"(.+(\r\n)*.*)", data, re.UNICODE)
         if(m is None):
            return False
         else:
            return (m.group(0) == data)

      elif(data_type == "M"):
         # MultilineString
         m = re.match(r"(.+(\r\n)*.*)", data)
         if(m is None):
            return False
         else:
            return (m.group(0) == data)

      elif(data_type == "L"):
         # Location
         pattern = re.compile(r"([EWNS]{1})", re.IGNORECASE)
         m_directional = pattern.match(data, 0)
         if(m_directional is None):
            # Did not match anything.
            return False
         else:
            pattern = re.compile(r"([0-9]{3})")
            m_degrees = pattern.match(data, 1)
            if((m_degrees is None) or int(m_degrees.group(0)) < 0 or int(m_degrees.group(0)) > 180):
               # Did not match anything.
               return False
            else:
               pattern = re.compile(r"([0-9]{2}\.[0-9]{3})")
               m_minutes = pattern.match(data, 4)
               if((m_minutes is None) or float(m_minutes.group(0)) < 0 or float(m_minutes.group(0)) > 59.999):
                  # Did not match anything.
                  return False
               else:
                  # Make sure we match the whole string,
                  # otherwise there may be an invalid character after the match. 
                  return (len(data) == 10)


      elif(data_type == "E" or data_type == "A"):
         # Enumeration, AwardList.
         # We'll assume that this data is valid already,
         # since the user can only select from a pre-defined (valid) list.
         return True

      else:
         return True
      
   
class TestADIF(unittest.TestCase):
   def test_adif_read(self):
      adif = ADIF()
      f = open("../ADIF.test_read.adi.test", 'w')
      f.write('''Some test ADI data.<eoh>

<call:4>TEST<band:3>40M<mode:2>CW
<qso_date:8:d>20130322<time_on:4>1955<eor>''')
      f.close()
    
      records = adif.read("../ADIF.test_read.adi.test")
      
      assert records == [{'BAND': '40M', 'TIME_ON': '1955', 'CALL': 'TEST', 'MODE': 'CW', 'QSO_DATE': '20130322'}]
              
if(__name__ == '__main__'):
   unittest.main()

