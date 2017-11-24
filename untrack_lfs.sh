#!/bin/sh

git filter-branch -f --prune-empty --tree-filter "
    # untrack all lfs files in all revisions first all file extensions
    for FILE_EXT in $(git lfs ls-files | cut -d ' ' -f 3 | cut -d '.' -f 2); do
        git lfs untrack $FILE_EXT;
    done

    # afterwards everything that's left
    for FILE in $(git lfs ls-files | cut -d ' ' -f 3); do
        git lfs untrack $FILE
    done

    if [ -f \".gitattributes\" ]; then
        git rm .gitattributes
    fi
" -- --all
