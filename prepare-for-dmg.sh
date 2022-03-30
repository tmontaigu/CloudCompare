ROOT=$PWD
PREFIX=pkg


DIR=$PREFIX/CloudCompare-x86_64
mkdir -p $DIR
rm -rf $DIR/CloudCompare.app
cp -a $PREFIX/build-release-x86_64/install/CloudCompare/CloudCompare.app $DIR
cp CHANGELOG.md $DIR
cp license.txt $DIR
cp global_shift_list_template.txt $DIR

./macdeploycc.py --sign  $DIR/CloudCompare.app
ditto -c -k -rsrc --sequesterRsrc --keepParent $DIR/CloudCompare.app $PREFIX/CloudCompare-x86_64.zip


DIR=$PREFIX/CloudCompare-arm64
mkdir -p $DIR
rm -rf $DIR/CloudCompare.app
cp -a $PREFIX/build-release-arm64/install/CloudCompare/CloudCompare.app $DIR
cp CHANGELOG.md $DIR
cp license.txt $DIR
cp global_shift_list_template.txt $DIR

./macdeploycc.py --sign  $DIR/CloudCompare.app
ditto -c -k -rsrc --sequesterRsrc --keepParent $DIR/CloudCompare.app $PREFIX/CloudCompare-arm64.zip

