#!/bin/sh

script_path=`dirname $0`

cd $script_path

find . -name *.DS_Store -type f -exec rm {} \;

for f in ./plugin.*
do
        echo "Plugin found: $f"
        version=`cat $f/addon.xml | grep -v 'xbmc.python' | sed -En 's/.*version="([[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+)"/\\1/p' | tr -d '\015\032'`
        addon_name=`basename $f`
        
        rm -f "$addon_name/$addon_name-$version.zip"
        zip -r "$addon_name/$addon_name-$version.zip" "$addon_name" -x "*.zip"
done

f=repository.likelion
echo "Repository found: $f"
version=`cat $f/addon.xml | sed -En 's/.*version="([[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+)"/\\1/p' | tr -d '\015\032'`
addon_name=`basename $f`
rm -f "$addon_name-$version.zip"
zip -r "$addon_name-$version.zip" "$addon_name" -x "*.zip"

python addons_xml_generator.py
