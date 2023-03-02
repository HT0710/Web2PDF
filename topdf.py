import getopt
import os
import sys
import pdfkit
import requests
from threading import Timer
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from bs4 import BeautifulSoup
from test import restart

SECTION = 0
URL = "https://docln.net/truyen/8904-nhuc-hinh-cong-chua-fremd-torturchen"


class TOPDF:
	def __init__(self):
		self.__url: str = URL
		self.__section: int = SECTION
		self.__page_html = None
		self.__series_name: str = ""
		self.__section_data: list = []
		self.__chapter_data: list = []
		self.__skip_existing: bool = True
		self.__section_merge: bool = True
		self.__timeout: int = 60
		self.__remove_comment_page = 0
		self.__pdf_options = {
			'page-size': 'A4',
			'margin-top': '0',
			'margin-right': '0',
			'margin-bottom': '0',
			'margin-left': '0',
			'encoding': "UTF-8",
			'no-outline': None
		}

	@staticmethod
	def remove_dot_folder(string):
		while string.endswith("."):
			string = string[:-1]
		return string

	@staticmethod
	def refine_string(string):
		for i in ["?", "@", "$", "%", "&", "\\", "/", "*"]:
			string = string.replace(i, '')
		for i in [">", "<"]:
			string = string.replace(i, '-')
		string = string.replace(":", " -")
		return string.strip()

	def Xchapter_format(self, name, i):
		name = self.refine_string(name)
		while name.find("  ") >= 0:
			name = name.replace("  ", " ")
		str_list = name.split(" ")
		if str_list.count("Chương") != 0:
			start = str_list.index('Chương') + 2
			name = " ".join(str_list[start:])
		return f"{str(i)} {name.strip()}"

	def chapter_format(self, name, i):
		name = self.refine_string(name)
		while name.find("  ") >= 0:
			name = name.replace("  ", " ")
		str_list = name.split(" ")
		if str_list.count("Chương") != 0:
			name = " ".join(str_list[1:])
		return f"{name.strip()}"

	def auto(self, argv):
		self.get_argv(argv)
		self.load_url()
		self.create_series_folder()
		self.get_chapter_data()
		self.create_section_folder()
		self.to_pdf()

	def get_argv(self, argv):
		opts, args = getopt.getopt(argv, "hu:s:mt:", ["help", "url=", "section=", "merge", "timeout="])
		for opt, arg in opts:
			if opt in ("-h", "--help"):
				print('topdf.py -u <https://docln.net/truyen/...> -s <Section number (Ex: 1, 2,... | 0 for all)>')
				sys.exit()

			elif opt in ("-u", "--url"):
				if not str(arg).startswith("https://"):
					arg = "https://" + arg
				if not str(arg).startswith("https://docln.net/truyen/"):
					print("Url must be 'docln.net/truyen/...' or 'https://docln.net/truyen/...'")
					sys.exit()
				else:
					self.__url = arg

			elif opt in ("-s", "--section"):
				if arg.lower() == "all":
					self.__section = 0
				try:
					arg = int(arg)
				except ValueError:
					print("Section must be a number.")
					sys.exit()
				if arg < 0:
					print("Section minimum is 1 or 0 for all.")
					sys.exit()
				elif arg > 10:
					print("Section maximum is 10 or 0 for all.")
					sys.exit()
				else:
					self.__section = arg

			elif opt in ("-m", "--merge"):
				self.__section_merge = True
			
			elif opt in ("-t", "--timeout"):
				try:
					arg = int(arg)
				except ValueError:
					print("Timeout must be seconds.")
					sys.exit()
				
				self.__timeout = arg

	def load_url(self):
		response = requests.get(self.__url)
		page = response.content
		html = BeautifulSoup(page, "html.parser")
		self.__page_html = html
		return self.__page_html, print("Load url - Done")

	def create_series_folder(self):
		series_name_class = self.__page_html.find(class_="series-name")
		series_name = series_name_class.getText().replace("\n", "")
		self.__series_name = self.refine_string(series_name)
		print(f"\nCreating folder: {self.__series_name}", end=" - ")
		if os.path.exists(self.__series_name):
			print("Existed")
		else:
			os.mkdir(self.__series_name)
			print("Created")
		return self.__series_name

	def get_chapter_data(self):
		sections = self.__page_html.find_all(class_="volume-list at-series basic-section volume-mobile gradual-mobile")
		sections = [sections[self.__section - 1]] if self.__section != 0 else sections
		total = 1
		for section in sections:
			sect_title = section.find_all(class_="sect-title")[0]
			title = sect_title.getText().replace("\n", "")
			title = self.remove_dot_folder(self.refine_string(title))
			chapter_data = section.find_all(class_='chapter-name')
			chapter_list = []
			for i, data in enumerate(chapter_data, total):
				chapter = data.find("a")
				chapter_name = chapter['title']
				chapter_name = self.chapter_format(chapter_name, i)
				chapter_url = chapter['href']
				chapter_url = f"https://docln.net{chapter_url}"
				chapter_list.append({
					'name': chapter_name,
					'url': chapter_url
				})
			self.__section_data.append({
				'title': title,
				'chapters': chapter_list
			})
			total += len(chapter_data)
		print("\nGet chapter data - Done")
		print(f"Total: {len(self.__section_data)} sections - {len([j for  j in self.__section_data])} chapters")
		return self.__section_data

	def create_section_folder(self):
		print("\nCreating folder:")
		for i, section in enumerate(self.__section_data, 1):
			print(f"\t{i}/{len(self.__section_data)}: {section['title']}", end=" - ")
			path = f"{self.__series_name}/{section['title']}"
			if os.path.exists(path):
				print("Existed")
			else:
				os.mkdir(path)
				print("Created")

	def to_pdf(self):
		print("\nTo PDF:", end="")
		print("\nSection merge - Enable", end="") if self.__section_merge else None
		total_section = len(self.__section_data)
		total_chapter = sum(len(j) for j in [i['chapters'] for i in self.__section_data])
		j = 0
		for section_number, section in enumerate(self.__section_data, 1):
			print(f"\n\t{section_number}/{total_section}: {section['title']}")
			path = f"{self.__series_name}/{section['title']}"
			for chapter_number, chapter in enumerate(section['chapters'], 1):
				j += 1
				print(f"\t\t{chapter_number}/{len(section['chapters'])} {j}/{total_chapter}: {chapter['name']}")
				if os.path.exists(f"{path}/{chapter['name']}.pdf") and self.__skip_existing:
					continue

				def timeout():
					restart()
					print(f"\nSystem timeout ({self.__timeout}s)")
					os._exit(1)
				timer = Timer(self.__timeout, timeout)
				timer.start()

				pdfkit.from_url(chapter['url'], 'raw.pdf', options=self.__pdf_options)

				reader = PdfReader('raw.pdf', strict=False)
				writer = PdfWriter()

				for page in range(len(reader.pages) - self.__remove_comment_page):
					p = reader.pages[page]
					writer.add_page(p)

				writer.add_metadata(reader.metadata)
				writer.add_metadata({"/Title": chapter['name']})
				writer.remove_links()

				with open(f"{path}/{chapter['name']}.pdf", "wb") as f:
					writer.write(f)
				writer.close()
				timer.cancel()

			if self.__section_merge:
				merge = PdfMerger()
				for chapter in section['chapters']:
					merge.append(PdfReader(f"{path}/{chapter['name']}.pdf", strict=False))
				with open(f"{self.__series_name}/{section['title']}.pdf", "wb") as f:
					merge.write(f)
				merge.close()
				print(f"\tMerged {len(section['chapters'])} chapters -> {section['title']}.pdf")

		os.remove("raw.pdf") if os.path.exists("raw.pdf") else None


if __name__ == "__main__":
	print("Ignore all warnings!", end="\n\n")

	process = TOPDF()
	process.auto(sys.argv[1:])

	print("-" * 5 + "> Complete <" + "-" * 5, end="\n\n")
	os._exit(0)
