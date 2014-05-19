# -*- coding: utf-8 -*-
# Copyright (c) 2014 Docker.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.




# import logging


# class ColorHandler(logging.StreamHandler):
#     LEVEL_COLORS = {
#         logging.DEBUG: '\033[00;32m',  # GREEN
#         logging.INFO: '\033[00;36m',  # CYAN
#         # logging.AUDIT: '\033[01;36m',  # BOLD CYAN
#         logging.WARN: '\033[01;33m',  # BOLD YELLOW
#         logging.ERROR: '\033[01;31m',  # BOLD RED
#         logging.CRITICAL: '\033[01;31m',  # BOLD RED
#     }

#     def format(self, record):
#         record.color = self.LEVEL_COLORS[record.levelno]
#         return logging.StreamHandler.format(self, record)

# logging.getLogger("docker_registry-core").addHandler(ColorHandler())

# log = logging.getLogger("docker_registry-core")

# log.debug("Debug")
# log.info("Info")
# log.warn("Warn")
# log.error("Error")
# log.critical("Critical")

# raise Exception("Stop")
