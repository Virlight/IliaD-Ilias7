# -*- coding: utf-8 -*-
"""
Product of cold-soda-jay

Utilities for data downloading and processing
"""
import time
import datetime
import os
import re
import zipfile
import getpass
import csv
import json
import bs4
import requests
import iliaD.cypter as cy
import filetype
# import mimetypes


from texttable import Texttable


class Session():
    """Session to login to ilias and download files.

    Attributes
    ----------
    target_directory: str
        default dirctory to save the documents
    path_of_data: str
        path of user login data and target directory data
    path_of_course: str
        path of Json file which contains user marked courses

    """

    target_directory = '../data/'  # the setting here will not be used, the target_directory will be assigned again upon request later .
    path_of_data = os.path.expanduser('~/IliasScraper')+'/data.csv'
    path_of_course = os.path.expanduser('~/IliasScraper')+'/course.json'
    base_url = "https://ilias.studium.kit.edu/"
    new_file_list = ""
    percent = 0


    def __init__(self, username=None, password=None):
        """
        Initiate the session and login to ilias.

        Attributes
        ----------
        user:str
            User name, in Format of 'uxxxx'
        password: str
            Password for login
        """
        if username and password:
            self.session = requests.Session()
            self.bs4_soup = self.login(username, password)


    def login(self, username, password):
        """
        Login to ilias and return bs4 object.

        input
        ---------

        user:str
            User name, in Format of 'uxxxx'
        password: str
            Password for login

        return
        --------
        :bs4.BeautifulSoup
        """
        payload = {"sendLogin": 1,
                   "idp_selection": "https://idp.scc.kit.edu/idp/shibboleth",
                   "target": "https://ilias.studium.kit.edu/shib_login.php", 
                   "home_organization_selection": "Mit KIT-Account anmelden"}
        response = self.session.post(
            "https://ilias.studium.kit.edu/Shibboleth.sso/Login",
            data=payload)

        shibo = bs4.BeautifulSoup(response.text, 'html.parser')
        csrf = shibo.find('input', attrs={'name':'csrf_token'}).attrs['value']

        # parse and login
        credentials = {"_eventId_proceed": "", "j_username": username, "j_password": password, "csrf_token": csrf}
        url = response.url
        ilias_response = self.session.post(url, data=credentials)

        html_doc = ilias_response.text

        soup = bs4.BeautifulSoup(html_doc, 'html.parser')
        relay_state = soup.find('input', attrs={'name': 'RelayState'})
        saml_response = soup.find('input', attrs={'name': 'SAMLResponse'})

        if not relay_state:
            print('Wrong credentials!')
            raise Exception('wrong credentials!')

        payload = {'RelayState': relay_state['value'],
                   'SAMLResponse': saml_response['value'],
                   '_eventId_proceed': ''}
        dashboard_html = self.session.post(
            "https://ilias.studium.kit.edu/Shibboleth.sso/SAML2/POST",
            data=payload).text
        
        # go to specified page
        specified_url = "https://ilias.studium.kit.edu/ilias.php?cmdClass=ilmembershipoverviewgui&cmdNode=j2&baseClass=ilmembershipoverviewgui"
        specified_page_response = self.session.post(specified_url)
        dashboard_html = specified_page_response.text

        return bs4.BeautifulSoup(dashboard_html, 'html.parser')


    def get_courses(self):
        """
        Extract courses items
        """
        # a_tags = self.bs4_soup.find_all('a', class_='il_ContainerItemTitle')

        # with open(os.path.expanduser('~/IliasScraper') + "/dashboard.html", "w", encoding='utf-8') as file:
        #     file.write(self.bs4_soup.prettify())

        div_tags = self.bs4_soup.find_all('div', class_='il-item-title')
        a_tags = []

        for div_tag in div_tags:
            # select("div>a") return list, so you muss extract by using index at first.
            # a_tags += [div_tag.select("div>a")]
            # in order to save process, we use find("a"), which return the fisrt <a> in the partial html.text.
            a_tags += [div_tag.find('a')]

        return [self.format_tag(a_tag) for a_tag in a_tags if a_tag is not None]
    

    def format_tag(self, a_tag):
        """
        extract all course name and thire href 
        """
        # base_url = "https://ilias.studium.kit.edu/"
        href = a_tag["href"]
        if not re.match(self.base_url, href):
            href = self.base_url + href

        return {"name": a_tag.contents[0], "href": href}


    def get_id(self, soup, current_directory):
        """
        Get all avaliable ids
        :param soup: current html text that represeents a course or a document repository
        :param curent_directory: local directory, where the docu in this web should be stored
        :return:
        """
        rtoken = soup.select('#mm_search_form')[0]['action']
        rt = re.findall(r"rtoken=.*\&",rtoken)[0][7:-1]
        id_list = [["token", rt, None, None]]
        # TODO: use ('div', class_='ilCLI ilObjListRow row') can skip the forum and video archive and get more exact documents, 
        # compared with (‘a’, class="il_ContainerItemTitle")
        row_list = soup.find_all('div', class_='ilCLI ilObjListRow row')
        for row in row_list:
            try:
                info = row.select("div.ilContainerListItemOuter > div > div.il_ContainerListItem > div > h3 >a")[0]
                url = info['href']
                if '_download' in url:     
                    # if there is a "_download" in url, it means this url is a download link. This docu will be downloaded within this method.
                    id_temp = re.findall(r"file_.*_download",url)[0][5:-9]
                    extension = row.select("div.ilContainerListItemOuter > div > div.il_ContainerListItem > div > span")[0].text.strip()
                else:
                    # if there is a "&cmd=view" in url, it means this url is a documental repository. It will recall the parent method recursively.
                    id_temp = re.findall(r"ref_id=.*&cmd=view",url)[0][7:-9]
                    self.download([{"name":info.text, "href": self.base_url + url}], current_directory)
                    continue
                id_list.append([info.text, id_temp, url, extension])
            except Exception :
                continue
        # This is another type of repository thst is relatively rare, the icon for which is an image of a card.
        card_list = soup.find_all('div', class_='il-card thumbnail')
        for card in card_list:
            try:
                card_info = card.select("div.caption.card-title > a")[0]
                url = card_info['href']
                if '_download' in url:
                    # if there is a "_download" in url, it means this url is a download link. This docu will be downloaded within this method.
                    id_temp = re.findall(r"file_.*_download",url)[0][5:-9]
                    file_name, extension = os.path.splitext(card.select("div.caption.card-title > a")[0].text)
                else:
                    # if there is a "&cmd=view" in url, it means this url is a documental repository. It will recall the parent method recursively.
                    id_temp = re.findall(r"ref_id=.*&cmd=view",url)[0][7:-9]
                    self.download([{"name":card_info.text, "href": self.base_url + url}], current_directory)
                    continue
                id_list.append([file_name, id_temp, url, extension])
            except Exception :
                continue
            # try:
            #     if info['target'] == '_top':
            #         continue
            # except:
            #     pass
            #
            # try:
            #     # only download file und folder
            #     url = info['href']
            #     if '_download' in url:
            #         id_temp = re.findall(r"file_.*_download",url)[0][5:-9]
            #     else:
            #         id_temp = re.findall(r"ref_id=.*&cmd=view",url)[0][7:-9]
            #     id_list.append(id_temp)
            # except:
            #     continue
        return id_list


    def download_zip(self,course,course_name,id_list,cmd,part):
        pay_load={}
        domain = re.findall(r"http.*&cmdClass=ilrepositorygui",course)[0]
        url = domain + "&cmd=post"+cmd+"&rtoken=" + id_list[0][1]
        course_path = self.target_directory + course_name + "/"
        course_part = part/len(id_list[1:])
        for id in id_list[1:]:
            try:
                pay_load["id[]"] = id[1]
                pay_load["cmd[download]"] = "Herunterladen"
                response = self.session.request(method='post',
                    url=url,
                    data=pay_load)
                extension = filetype.guess(response.content).EXTENSION

                file_path = course_path + id[0]+"."+extension
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                if extension == "zip":
                    self.extract_file(file_path, course_path, course_part,course_name)
                    os.remove(file_path)
                else:
                    self.percent += course_part
                    print('\r',
                          '[ ' + '#' * int(self.percent * 30) + '>' + '%.2f'%(self.percent * 100) + '%' + ' ' * (
                              30 - int(self.percent * 30)),
                          end=' ] Downloading {%s}'%course_name, flush=True)
            except:
                self.percent += course_part
                print('\r',
                          '[ ' + '#' * int(self.percent * 30) + '>' + '%.2f'%(self.percent * 100) + '%' + ' ' * (
                              30 - int(self.percent * 30)),
                          end=' ] Downloading {%s}'%course_name, flush=True)
                continue


    def extract_file(self,path, course_path, course_part,course_name):
        try:
            with zipfile.ZipFile(path, 'r') as z:
                zippart = course_part / len(z.namelist())
                cache_folder = ''
                for file_name in z.namelist():
                    if os.path.isfile(path[:-4] + '/' + file_name):
                        continue
                    z.extract(file_name,course_path)#, path[:-4]
                    if file_name.endswith('/') and file_name.count('/') == 1:
                        self.new_file_list += '%s~ %s\n' % (4 * ' ', file_name)
                        cache_folder = file_name
                    else:
                        self.new_file_list += '%s- %s\n' % (8 * ' ', file_name.replace(cache_folder, ''))
                    self.percent += zippart
                    print('\r',
                              '[ ' + '#' * int(self.percent * 30) + '>' + '%.2f'%(self.percent * 100) + '%' + ' ' * (
                                  30 - int(self.percent * 30)),
                              end=' ] Downloading {%s}'%course_name, flush=True)
        except zipfile.BadZipFile:
            pass


    def download_directly(self, id_list, directory, course_name, part):
        course_part = part/len(id_list[1:])
        for item in id_list:
            try:
                docu_name, _, url, extension = item
                local_filename = directory + '/' + docu_name
                self.download_file(url, local_filename, extension)

                self.percent += course_part
                print('\r',
                        '[ ' + '#' * int(self.percent * 30) + '>' + '%.2f'%(self.percent * 100) + '%' + ' ' * (
                            30 - int(self.percent * 30)),
                        end=' ] Downloading {%s}-{%s}'%(course_name, docu_name), flush=True)
            except:
                self.percent += course_part
                print('\r',
                            '[ ' + '#' * int(self.percent * 30) + '>' + '%.2f'%(self.percent * 100) + '%' + ' ' * (
                                30 - int(self.percent * 30)),
                            end=' ] Downloading {%s}-(%s)'%(course_name, docu_name), flush=True)
                continue


    def download_file(self, url, local_filename, extension):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Referer": url
        }

        # Send a HTTP request to the URL.
        with self.session.get(url, stream=True, headers=headers) as r:
            # Throw an error if the request was unsuccessful.
            r.raise_for_status()

            # Guess the filetype
            # content_type = r.headers['content-type']
            # extension = mimetypes.guess_extension(content_type)
            # # Sometimes, .jpe will be returned for image/jpeg mime type, which we replace with .jpg
            # if extension == ".jpe":
            #     extension = ".jpg"
            
            # Add the guessed extension to the document name
            local_filename = f"{local_filename}.{extension}"
            
            # Open the file in write mode.
            with open(local_filename, 'wb') as f:
                # Write the contents of the response to the file.
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename


    def download(self, courses, target=None):
        """
        Download all marked courses and save them into target directory
        
        Attribute
        ---------
        courses: dict
            A dictionary of courses. one course is represented as {name:"...", href:"..."}
        target: str
            The path of target directory

        Return
        --------
            :list of new added file

        """
        if target:
            target_directory = target
        else: 
            target_directory = self.target_directory
        if target_directory[-1] not in ['/','\\']:
            target_directory += '/'
        self.percent = 0
        self.new_file_list = ''
        print('Downloading...')
        part = 1 / len(courses)

        for course in courses:
            print('\r',
                  '[ ' + '#' * int(self.percent * 30) + '>' + '%.2f'%(self.percent * 100) + '%' + ' ' * (
                      30 - int(self.percent * 30)),
                  end=' ] Downloading {%s}'%course['name'], flush=True)
            link = course["href"]
            course_name = course['name']
            if '/'in course_name or ':' in course_name :
                course_name = course_name.replace('/', '&&')
                course_name = course_name.replace(':', '&&')

            try:
                os.mkdir(target_directory + course_name)
            except:
                pass
            self.new_file_list+='\n# %s\n'%course_name
            html = self.session.get(link).text
            soup = bs4.BeautifulSoup(html, 'html.parser')

            # TODO: crucial stage for downloading all the documents.
            # NOTE: firstly get the course's href. 
            # with open(os.path.expanduser('~/IliasScraper') + f"/{course_name}.html", "w", encoding='utf-8') as file:
            #     file.write(soup.prettify())
            dropdown = soup.find_all("div",{"id": "tttt"})[0].find_all("ul", {"class": "dropdown-menu pull-right"})[0]

            cmd_tmp = dropdown.select("li>a")[1]['href']
            cmd = re.findall("&cmdNode.*",cmd_tmp)[0]

            # NOTE: secondly, get the directly-downloadable id list. if there are repositories in web, it will be recursively downloaded in method get_id()
            id_list = self.get_id(soup, target_directory + course_name)
            if len(id_list) == 1:
                self.percent += part
                print("id list only has one element")
                continue

            # NOTE: thirdly, start to download documents. But the previous method:self.download_zip() of directly downloading zip files from the course homepage is no longer applicable. We are adopting a new approach by directly accessing each repository for download, which will be simpler.
            # self.download_zip(link,course_name,id_list,cmd,part)
            self.download_directly(id_list, target_directory + course_name, course_name, part)
            

        self.percent = 1
        print('\r',
              '[ ' + '#' * int(self.percent * 30) + '>' + '%.2f'%(self.percent * 100) + '%' + ' ' * (
                  30 - int(self.percent * 30)),
              end=' ]', flush=True)
        print('\nDone!')
        return self.new_file_list


    def get_marked_course_list(self,read=False):
        """
        Get marked courses from course.json. If the file not exist, then choose the course.

        return
        -------
        marked_course:list
        """
        if read:
        #     marked_course = self.choose_course()
        #     return marked_course
            try:
                with open(self.path_of_course, "r") as file:
                    marked_course = json.loads(file.read())
                return marked_course
            except:
                print('No Marked Course!')
                marked_course = self.choose_course()
                return marked_course
        else:
            marked_course = self.choose_course()
            return marked_course

    def choose_course(self):
        """
        Choose the course to download
        """
        raw_list = self.get_courses()
        t = Texttable()
        table=[["Nr.", "Course"]]
        i = 1
        for course in raw_list:
            if course is None: continue
            table.append([i,course['name']])
            i += 1
        t.add_rows(table)
        dialog=True
        print(t.draw())
        marked = []
        while dialog:
            confirm=True
            marked = []
            numbers = input('Choose couses by typing the number of course, separate with \' , \' :')
            for num in numbers.split(','):
                try:
                    if raw_list[int(num)-1] not in marked:
                            marked.append(raw_list[int(num)-1])
                            print('%s. %s'%(str(len(marked)),raw_list[int(num)-1]['name']))
                except:
                    print('Ivalid input!: %s'%num)
                    confirm = False
                    break

            while confirm:
                answer=input('\nThoses are choosed courses.\nConfirm?(y/n)')
                if answer=='y':
                    dialog=False
                    break
                elif answer!='n':
                    print('Ivalid input!')
                    continue
                break
        with open(self.path_of_course, "w") as file:
            json.dump(marked, file)
        print('\nSaved to %s!\n'%self.path_of_course)    
        return marked


class Synchronizer:
    """
    A synchronizer which allows user to login ,download, check user data
    """
    path_of_data = os.path.expanduser('~/IliasScraper')+'/data.csv'
    path_of_course = os.path.expanduser('~/IliasScraper')+'/course.json'


    def init_login_data(self, user=None, target=None, password=False):
        """
        Initiate login data
        """
        if password:
            pwd = getpass.getpass("Please give password(Pw won't show in Terminal): ")
            self.write_user_data('pwd',cy.enCode(pwd))
            return None
        if not user:
            user = input('Please give username (U-Account):\n')
            if target == 'ch':
                self.write_user_data('user',user)
                return None
        if not target:
            target = input('Please give target directory:\n')
            if user == 'ch':
                if not (target.endswith('\\') or target.endswith('/')):
                    target += '/'
                self.write_user_data('target', target)
                return None

        if not (target.endswith('\\') or target.endswith('/')):
            target+='/'
        with open(self.path_of_data, 'w', newline='', encoding='utf-8') as csvfile:
            spamwriter = csv.writer(csvfile)
            spamwriter.writerow(['key','value'])
        pwd = getpass.getpass("Please give password(Pw won't show in Terminal): ")
        with open(self.path_of_data, "a+") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['user',user])
            writer.writerow(['pwd',cy.enCode(pwd)])
            writer.writerow(['target',target.replace('\\','/')])
        return pwd


    def synchronize(self):
        startt = time.time()
        try:
            session, target = self.login()
        except:
            return
        
        print('%s: Login succeed!'%(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        courslist = session.get_marked_course_list(read=True)
        print('%s: Checking courses...'%(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        new_file_list = session.download(courslist,target)
        print('Time coast:%.2f\n%s: New files:'%((time.time()-startt),
                                                 (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))
        print(new_file_list)


    def login(self):
        user = ''
        pwd = ''
        target = ''
        try:
            with open(self.path_of_data, 'rt', encoding='utf-8') as fp:
                reader = csv.DictReader(fp)
                for row in reader:
                    if row['key'] == 'target':
                        target = row['value']
                    elif row['key'] == 'user':
                        user = row['value']
                    elif row['key'] == 'pwd':
                        pwd = cy.deCode(row['value'])
            if user == '' or pwd == '' or target == '':
                print('No Data!')
                print('Please initialize user configuration at first!!\n')
                return None
            session = Session(username=user, password=pwd)
            return session, target
        except:
            print('Error!')
            print('Please initialize user configuration at first!!\n')
            return None


    def show_user_data(self):
        try:
            with open(self.path_of_data, 'rt', encoding='utf-8') as fp:
                reader = csv.DictReader(fp)
                for row in reader:
                    if row['key'] == 'target':
                        target = row['value']
                    elif row['key'] == 'user':
                        user = row['value']
                    elif row['key'] == 'pwd':
                        pwd = cy.deCode(row['value'])
            if user == '' or pwd == '' or target == '':
                print('No Data!')
                print('Please initialize user configuration at first!!')
                return None
            print('\nusername: %s\n\nTarget folder: %s\n'%(user,target))
            while True:
                answer = input('Do you want to check password?\n(y/n)')
                if answer =='y':
                    npwd = getpass.getpass("Please give password to check if the stored pw right (Pw won't show in Terminal): ")
                    if pwd==npwd:
                        print("\nPassword match!")
                    else:
                        print('\nPassword dosen\'t match!')
                elif answer !='n':
                    print('Ivalid input!')
                    continue
                break
            while True:
                change_question = input('Do you want to edit user name, target directory or password?\n(y/n)')
                if change_question == 'y':
                    while True:
                        yChange = input('Which one do you want to change?\n\n1. User name\n2. Target directory\n3. Password\n4. All\n5. Cancel\n')
                        if yChange == '1':
                            self.init_login_data(target='ch')
                        elif yChange == "2":
                            self.init_login_data(user='ch')
                        elif yChange == "3":
                            self.init_login_data(password=True)
                        elif yChange == "4":
                            self.init_login_data()
                        elif yChange == "5":
                            return
                        else:
                            print('Ivalid input!')
                            continue
                        while True:
                            cont=input('Do you want to edit anything else?\n(y/n)')
                            if cont == 'y':
                                break
                            elif cont == 'n':
                                return
                            else:
                                print('Ivalid input!')
                                continue
                elif change_question != 'n':
                    print('Ivalid input!')
                    continue
                break
        except:
            print('No Data!')
            print('Please initialize user configuration at first!!\n')
            return None


    def show_marked_course(self):
        #try:
        # except:
        #     return
        try:
            with open(self.path_of_course, "r") as file:
                clist = json.loads(file.read())
        except:
            session, target= self.login()
            clist=session.get_marked_course_list()
        out='\nChoosed courses:\n'
        if clist is None:
            return
        for counter, value in enumerate(clist):
            out+='\n%s: %s\n'%(str(counter+1),value['name'])
        print(out)
        while True:
            answer=input('Do you want to edit course list?\n(y/n)')
            if answer == 'y':
                self.change_marked_course()
            elif answer != 'n':
                print('Ivalid input!')
                continue
            break


    def change_marked_course(self):
        session, target = self.login()
        session.choose_course()


    def write_user_data(self,key, value):
        csvdict = csv.DictReader(open(self.path_of_data, 'rt', encoding='utf-8', newline=''))
        dictrow = []
        for row in csvdict:
            if row['key'] == key:
                row['value'] = value
            # rowcache.update(row)
            dictrow.append(row)

        with open(self.path_of_data, "w+", encoding='utf-8', newline='') as lloo:
            # lloo.write(new_a_buf.getvalue())
            wrier = csv.DictWriter(lloo, ['key', 'value'])
            wrier.writeheader()
            for wowow in dictrow:
                wrier.writerow(wowow)

