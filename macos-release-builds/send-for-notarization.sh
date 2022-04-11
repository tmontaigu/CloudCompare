echo "Enter AppleId email:"
read APPLE_ID_EMAIL

xcrun altool --notarize-app --primary-bundle-id org.cloudcompare.cloudcompare -u $APPLE_ID_EMAIL --file pkg/CloudCompare-x86_64.zip
xcrun altool --notarize-app --primary-bundle-id org.cloudcompare.cloudcompare -u $APPLE_ID_EMAIL --file pkg/CloudCompare-arm64.zip
