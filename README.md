Venture
=======

Venture is an interactive, Turing-complete probabilistic programming
platform that aims to be sufficiently expressive, extensible, and
efficient for general-purpose use.

http://probcomp.csail.mit.edu/venture/

Venture is rapidly-evolving, **alpha quality** research software. The
key ideas behind its design and implementation have yet to be
published. We are making Venture available at this early stage
primarily to facilitate collaboration and support the emerging
probabilistic programming community.

Installing Venture from Source
==============================

This release is for early adopter types who are
willing to put up with much of the pain that a more mature software
package would not impose.  In particular, documentation is sparse and
the user interface is unforgiving.  Often, the only way to learn
what's going on will be to ask us or to read the source code.

Dependencies
------------

Here is what we install on a clean Ubuntu 12.04 (or higher).

    # Get system dependencies
    sudo apt-get install -y libboost-all-dev libgsl0-dev python-pip ccache libfreetype6-dev
    # Must update distribute before requirements.txt install
    sudo pip install -U distribute

    # [Optional] Get Python dependencies (faster to install prepackaged than via pip)
    # Also pulls in required external libraries
    sudo apt-get install -y python-pyparsing python-flask python-requests python-numpy python-matplotlib python-scipy

Installation to global environment
----------------------------------

    sudo pip install -r requirements.txt
    sudo python setup.py install

Installation to local environment
---------------------------------

Download and install python "virtualenv" onto your computer.
https://pypi.python.org/pypi/virtualenv

Create a new virtual environment to install the requirements:

    virtualenv env.d
    source env.d/bin/activate
    pip install -r requirements.txt

Installation into your virtual environment:

    python setup.py install

Checking that your installation was successful
----------------------------------------------

    ./sanity_tests.sh

If you are interested in improving Venture, you can also run

    ./list_known_issues.sh

Getting Started
---------------

-   Interactive Venture console:

        venture

    You might like to type in the [trick coin
    example](http://probcomp.csail.mit.edu/venture/console-examples.html)
    to start getting a feel for Venture.

-   Venture as a library in Python:

        python -i -c 'from venture import shortcuts; ripl = shortcuts.make_church_prime_ripl()'

    Using Venture as a library allows you to drive it
    programmatically.  You might like to peruse the
    [examples](http://probcomp.csail.mit.edu/venture/library-examples.html)
    for inspiration.

-   You can find two advanced examples in the `examples/` directory.
    These rely on VentureUnit (included), an experimental inference
    visualization wrapper using Venture as a library.


Developing Venture
==================

The interesting parts of the code are:
- The stack (including SIVM, RIPL, VentureUnit, server, and Python client) in `python/`
- The C++11 engine (plus a thin Python driver) in `backend/cxx/`
- The actual entry points are in `script/`
- Advanced example programs live in `examples/`
- The Javascript client and web demos are actually in the
  [VentureJSRIPL](https://github.com/mit-probabilistic-computing-project/VentureJSRIPL)
  repository.
- There are language-level benchmarks (and correctness tests) in the
  [VentureBenchmarksAndTests](https://github.com/mit-probabilistic-computing-project/VentureBenchmarksAndTests)
  repository.

Python Development
------------------

We recommend using ipython for Venture development; you can obtain it via

    pip install ipython

If you are developing the python libraries, you will
likely be running the installation script hundreds of
times. This is very slow if you don't have a c++ compiler
cache installed. Here is a quick shell command (aliased in
my bashrc file) which automatically resets the virtual
environment and reinstalls the module, using the compiler
cache. Make sure that the additional python dependencies
are installed in the global python environment.

    deactivate && rm -rf env.d build && virtualenv --system-site-packages env.d && \
      . env.d/bin/activate && CC="ccache gcc" python setup.py install
