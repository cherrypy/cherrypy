function before_install {
    if [[ "$TRAVIS_OS_NAME" == "osx" ]]
    then
        export CC=clang
        export CXX=clang++
        get_macpython_environment $MB_PYTHON_VERSION venv
    else
        virtualenv --python=python venv
    fi
    source venv/bin/activate
    python --version # just to check
    pip --version
    if [[ "${MB_PYTHON_VERSION:0:3}" != "3.2" ]]
    then
        pip install --upgrade pip
    fi
    pip install --upgrade wheel
    pip --version
}
