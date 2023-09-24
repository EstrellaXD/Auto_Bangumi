#!/usr/bin/env bash

#
# Usage:
#   `bash scripts/pip-lock-version.sh`
#
# ```prompt
# Lock the library versions in `requirements.txt` to the current ones from `pip freeze` using shell script,
# but don't change any order in `requirements.txt`
# ```
#


# Create a temporary requirements file using pip freeze
pip freeze > pip_freeze.log

# Read the existing requirements.txt line by line
while IFS= read -r line
do
    # Extract the library name without version
    lib_name=$(echo $line | cut -d'=' -f1)

    # Find the corresponding library in the temporary requirements file
    lib_line=$(grep "^$lib_name==" pip_freeze.log)

    # If the library is found, update the line
    if [[ $lib_line ]]
    then
        echo $lib_line
    else
        echo $line
    fi

# Redirect the output to a new requirements file
done < requirements.txt > new_requirements.log

# Remove the temporary requirements file
rm pip_freeze.log

# Replace the old requirements file with the new one
mv new_requirements.log requirements.txt

