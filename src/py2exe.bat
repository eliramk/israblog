copy download_blog_posts.py .\temp\
cd temp
cd dist
del /Q download_blog_posts\*.*
rmdir download_blog_posts
cd ..
chcp 1255
pyinstaller download_blog_posts.py
pause
copy dist\download_blog_posts\*.* ..\dist\download_blog_posts\
cd ..
copy download_blogs.bat dist\download_blog_posts\
chcp 65001
