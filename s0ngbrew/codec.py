#!/usr/bin/env python3

import os
import zlib
from struct import pack, unpack


class FileCountError(Exception):
	pass


class ChecksumError(Exception):
	pass


class Codec(object):
	"""\
	Main codec for DRP.
	"""
	def __init__(self, ifname='', ofname='', is_bin=True):
		self.ifname = ifname
		#Currently automatic ofname doesn't work due to cli.py
		if ofname == "":
			self.ofname = os.path.splittext(ifname)[0]+".xml"
		else:
			self.ofname = ofname
		self.is_bin = is_bin
		self.iofunc = (self.encode, self.decode)[self.is_bin]

	def run(self):
		"""\
		Run the codec and write the output file.
		"""
		with open(self.ifname, 'rb') as f:
			self.iofunc(f)

	def encode(self, f):
		"""\
		Encode DRP: Boilderplate header and XML compression
		"""
		if os.path.basename(self.ofname) == "musicInfo.drp":
			type = 0
		elif os.path.basename(self.ofname) == "katsu_theme.drp":
			type = 1
		else:
			print("Please name your output file correctly. It should be musicInfo.drp or katsu_theme.drp.")
			sys.exit()
		
		rxml_data = f.read()
		bxml_data = zlib.compress(rxml_data)
		bxmls = (len(bxml_data) + 12) if type == 0 else (len(bxml_data) + 8) # 12 for Taiko 3, 4 for Taiko 1.. And 8 for katsu_theme
		checksum = len(rxml_data)
		#Margin is different for katsu
		unknown_margin = (0x20000001, 0x0310, 0x00010001, 0) if type == 0 else (0x20000001, 0x01B0, 0x00010001, 0)
		quadup = lambda x: (x, x, x, x)
		align = lambda x: x * b'\x00'

		with open(self.ofname, 'wb') as of:
			unknown, filecount = 2, 1
			of.seek(0x14)
			of.write(pack('>HH', unknown, filecount))
			of.seek(0x60)
			# Notice: the original musicInfo.drp stores the filename
			# `musicinfo_db`, which might be game-specific
			if type == 0:
				of.write(bytes("musicinfo_db".encode('ascii')))
			if type == 1:
				of.write(bytes("katsu_theme_db".encode('ascii')))
			
			of.seek(0xa0) #Jump to A0 (Where the unknown string is written and the rest of it)
			of.write(pack('>9I',
				*unknown_margin,
				*quadup(bxmls), #???
				checksum))
			of.write(bxml_data)

			remain = of.tell() % 0x10
			if remain: of.write(align(0x10 - remain))
				
	def decode(self, f):
		"""\
		Decode DRP: Decompress XML data
		"""
		f.seek(0x14)
		unknown, filecount = unpack('>HH', f.read(4))

		if filecount != 1:
			#TODO...
			print('Not a single XML compressed file, internal names will be used instead.')

		f.seek(0x60)
		for i in range(filecount):
			fname = f.read(0x40).split(b'\x00')[0].decode("utf-8")
			print(fname)
			#No idea what this line is.
			f.read(0x10)
			# bxmls: binary XML size (zlib compressed), rxmls: Raw XML size
			# the 4 bxmls are duplicate, and rxmls is for checksum
			bxmls, bxmls2, bxmls3, bxmls4, rxmls = unpack('>5I', f.read(4 * 5))
			bxml_data = f.read(bxmls - 4) # rxmls is an unsigned integer

			if bxmls > 80:
				bxml_data = zlib.decompress(bxml_data) # no Unix EOF (\n)

			if len(bxml_data) != rxmls:
				raise ChecksumError('Checksum failed, file might be broken')

			if filecount == 1:
				with open(self.ofname, 'wb') as of:
					of.write(bxml_data)
			else:
				with open(fname+".xml", 'wb') as of:
					of.write(bxml_data)
