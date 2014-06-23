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

#  ___          _    _      ___
# |   \ _ _ ___(_)__| |___ / __|___ _ _ ___
# | |) | '_/ _ \ / _` |___| (__/ _ \ '_/ -_)
# |___/|_| \___/_\__,_|    \___\___/_| \___|

"""
Docker Registry Core
~~~~~~~~~~~~~~~~~~~~~

The core of the registry. Defines helper methods and generics to be used by
either the registry itself, or drivers packages.

:copyright: (c) 2014 by Docker.
:license: Apache 2.0, see LICENSE for more details.

"""

from __future__ import absolute_import
import logging

__author__ = 'Docker'
__copyright__ = 'Copyright 2014 Docker'
__credits__ = []

__license__ = 'Apache 2.0'
__version__ = '2.0.0'
__maintainer__ = 'Docker'
__email__ = 'dev@docker.com'
__status__ = 'Production'

__title__ = 'docker-registry-core'
__build__ = 0x000000

try:
    NullHandler = logging.NullHandler
except AttributeError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())


#                     ..II7N.. ..  ..
#                    .77I7II?7$$$$ZOO~.
#                . I7I7I$7$77$7II7ZZZZZO.
#      .....8$77I?I?I?$$77II77II7Z$ZZZO$ZOO..
#      .IIII77$?8I???$?I?I777I7$777$$$$O888O8 .
#      7~III777II???+I??7I7Z7I?I??$O8Z$ZZZ7O8D+8.
#      ?.?I7777Z?+=+$ODDIM7Z8I7$.+788OZ$8$77OO$$.
#     .DM7$$I$$7I$?78+O$$$++Z7I8NNNNNNNO$+NIIND8.
#       M$OODOO7INDNNN77?=+~~~+7NNNNNNN877N7$D.
#        .MNNDDDDODND7O8Z??=.$+?7NNNNM8D88Z$D..
#             ..:=7MDNNNNNDDNDNNDDNNNNNNM..
#        . . ..  .. .88$7NOO77$ZODO8D.. .........
#        ..OZOZOZ88DD8D8$D888DDDNDDNNNDO78D8DD7..
#    .Z77$$$$$Z$ZZZZZZZZ?I$ZOOOOOOZ$IOOOOOOOO$ZOOZZZ.
#     7?7?IIIII?7$7777777777$$$7$$Z$$77$$$ZZZ$OZOZ88D.
#     .O8MMMII7IID++=+????IIIII7II7II77$$$$OZODMMMNZ.
#    ..O$$O7$7777$78DDN7DNONO$ZZZO888OZZ$$OD8ZZ8ZOO..
#     7$$77$7$O$$$$ZO8O7O8ZZ?OI+?I$IO$Z$8$O8$78NZNI
#     ..IZ7$O$7$8$IOO7O78O$$+77II?ZIO$$ZZOO$7Z8O8DI.
#        .$7$$I88$777I$7OZ7$?IZI7+O+$$$OZOOIIONZODD
#           .~7OI77II??7O7II??Z?7?N?ZOZZZO8OO8$7O8.
#           ..ZNMNNMNMDZNN8NOZZZ8N7DNNDZDNO8ODD.. .
#            .$MNN8DN7$N8M8D$$$8NOOM:MNNNOD88$Z.
#           .7$II7OZDN..DOZ.  =+I77OI.I88D8N8$$O.
#          .$Z=I7OZZNN.+88.   .+7ZDM   DD8Z$$I$7$ .
#        ..7$. .ZOZODN.ZO7.      OO    .8OOZZ8$II7.
#        778...$DZDDD8.ZDZ.      Z$     .O8OI7O7II:
#      ?I?. . ..8O8OD,.$.=.      ~?..    .8O.~7II??..    .
#   ..7IZ..     =?OOZ..8... .    .?..    .88?..+II?I...
#  I87I..      .?.ZOOZ78$.       .7..      Z7Z~ .II+I..
# .D87. .        ?OOO.O8,..      .7..      .8.....+$+I
#  ..IO..        ?ZOO..8.        .7+.     ..O.,. ..?O??..
#    ..8+..     .:.OO7.$.  .     .~I.      .$. ~.  .7Z7D.   ..
#     .MID.      ..$O$.7.    .    .?.     .II. .7.=+ZD$.
#       ~:I..    .I$OZ8.O. .      .7~ .   .?$    ?++I..
#       ...I.    .:$I+N.$..       .?IO.    I.   .I+I.Z.
#        ..7O..   .:8D..7.. .    .:I?O.   .O.   =+~.Z..
#          .OO7.. .7OO. +$. .     :I.     .Z.  .=: .=..
#           .?..Z.IN?7. .Z       .7$      OZ=..==....
#              .  +I$    7.      Z$..    +.$. I=   =.
#              . IZZ... .7,.   ..Z...     ....+..  .
#              .=Z.,.    +$..   8I..         +?.. :.
#             ..$ ,..   ..Z..  .78.        .$O+?. I..
#             .Z,7.     .?IOO..   .        I+O7I?,.   .
#           .I8$+..     .IIZ8 .           ..ZDDI+7?+IM..  ?..  ...
#          +8DO.. .      ..M:..              ....  ...+==~=~~I78$,..I
#         I7IIO~.          7M                             .  ..+~.. .
#        ..7?Z$O...           .                          ...    .....
#           . ..OO...
#              ...$Z.
#                  ?$$..
#                  .?OO:.
#                  .+OI$
#                ..7..$
#                .. .7...
#                  ..=.
#                   7..
