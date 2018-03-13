from setuptools import setup

try:
    import pypandoc
    long_description = pypandoc.convert_file('README.md', 'rst', extra_args=())
except ImportError:
    import codecs
    long_description = codecs.open('README.md', encoding='utf-8').read()

long_description = '\n'.join(long_description.splitlines())

setup(
    name='discoverhue',
    description='Auto discovery of Hue bridges',
    long_description=long_description,
    version='1.0.2',
    url='https://github.com/Overboard/discoverhue',
    author='Overboard',
    license='MIT',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='philips hue',
    packages=['discoverhue'],
)
