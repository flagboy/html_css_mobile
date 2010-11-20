from setuptools import setup

name='HtmlCssInclude'
version='0.1'
short_description = 'HtmlCssInclude convert css to inline style for mobile'
long_description = file('README').read()

classifiers = [
   "Development Status :: 3 - Alpha",
   "License :: OSI Approved :: Python Software Foundation License",
   "Programming Language :: Python",
   "Topic :: Text Processing :: Markup :: HTML",
]

setup(
   name=name,
   version=version,
   description=short_description,
   long_description=long_description,
   classifiers=classifiers,
   auther='flagboy',
   author_email='hata.hirotaka@gamil.com',
   license='PSL'
)
