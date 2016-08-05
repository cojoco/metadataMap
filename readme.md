# Metadata Map

This runs the Metadata Map, both one-dimensional and two-dimensional versions.

# INSTALL

It is recommended that you use a virtual environment while running this.
You can set one up in './ENV' using 'virtualenv -p python3 ENV'.
Activate the virtual environment using '. ENV/bin/activate'.
When you are done with the virtual environment, you should type 'deactivate'.

You can install the dependencies using: 'pip install -r requirements.txt'

After installing these dependencies, you will need to go to
'./ENV/src/activetm/activetm/tech/sampler/' and type 'make' to make the sampler.
If you receive an error regarding BLAS or LAPACK, you may need to
'dnf install lapack-devel' (on Fedora) to get the development headers.

Finally, you will need a dataset. I've been using an Amazon reviews dataset,
but so long as you have something that's usable by Ankura it should be usable
here. You can pickle that data into a dataset.pickle file using the
'pickle\_data.py' script.
