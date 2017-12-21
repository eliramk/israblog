copy download_blog_posts.py .\temp\
cd temp
pyinstaller download_blog_posts.py
pause
copy dist\download_blog_posts\*.* ..\dist\download_blog_posts\
