# -*- coding: utf-8 -*-
# file: parser.py

"""
This file contains the Parser engine that can parse the EzDrama format to TEI/XML
See https://github.com/dracor-org/ezdrama for more details
Usage example in the ezparser.ipynb notebook: 
https://github.com/dracor-org/ezdrama/blob/main/ezdramaparser.ipynb
"""

# =================================
# Import statements
# =================================

import re
from datetime import datetime
from transliterate import translit
import yiddish
from bs4 import BeautifulSoup, Tag

# =================================
# Parser engine
# =================================

class Parser():
    '''This is the main class, the EzDrama to TEI/XML parser
    It generates an empty TEI/XML tree upon initalization
    And then using the '.parse_file' method one can parse a txt file 
    (providing the path to file as argument)

    Or using the lower-level '.parse_lines_to_xml' method one can parse 
    a list of ezdrama lines (providing the list of strings as argument)'''

    def __init__(self,
                 bracketstages = True,
                 is_prose = True,
                 dracor_id = 'insert_id',
                 dracor_lang = 'insert_lang'):
        ## initializing a new TEI/XML bs-tree that will be populated from ezdrama text:
        self.tree_root = Tag(name='TEI')
        self.tree_root['xmlns'] = "http://www.tei-c.org/ns/1.0"
        self.tree_root['xml:id'] = dracor_id 
        self.tree_root['xml:lang'] = dracor_lang
        
        ## creating and adding TEI <teiHeader> stub to be filled with metadata later
        self.__create_and_add_header()

        ## creating and adding TEI <standOff> stub
        self.__add_standoff()

        # creating TEI <text> stub to be filled with marked up play text later
        text = Tag(name='text')
        front = Tag(name='front')
        body = Tag(name='body')
        text.append(front)
        text.append(body)
        self.is_prose = is_prose
        self.tree_root.append(text)
        self.current_lowest_tag = body
        self.current_lowest_div = body
        self.current_lowest_div['level'] = 0

        # defining the set of EzDrama special symbols
        self.special_symb_list = '@$^#<'
        self.bracketstages = bracketstages
        
    ### Auxiliary methods for building TEI metadata structure (header/standoff) stub:
    
    def __create_and_add_header(self):
        header = Tag(name='teiHeader')
        fdesc = Tag(name='fileDesc')
        titlestmt = Tag(name='titleStmt')
        fdesc.append(titlestmt)
        self.__add_pbstmt(fdesc)
        self.__add_sourcedesc(fdesc)
        header.append(fdesc)
        self.tree_root.append(header)
        
    def __add_standoff(self):
        today = datetime.today().strftime('%Y')
        standoff_as_string = f'''
        <standOff>
            <listEvent>
            <event type="print" when="{today}">
            <desc/>
            </event>
            <event type="premiere" when="{today}">
            <desc/>
            </event>
            <event type="written" when="{today}">
            <desc/>
            </event>
            </listEvent>
            <listRelation>
            <relation name="wikidata" active="INSERT" passive="INSERT"/>
            </listRelation>
        </standOff>
        '''
        standoffsoup = BeautifulSoup(standoff_as_string, 'xml')
        standoff = standoffsoup.standOff
        self.tree_root.append(standoff)
        
    def __add_pbstmt(self, filedesc):
        pubstmt_as_string = """
          <publicationStmt>
            <publisher xml:id="dracor">DraCor</publisher>
            <idno type="URL">https://dracor.org</idno>
            <availability>
              <licence>
                <ab>CC0 1.0</ab>
                <ref target="https://creativecommons.org/publicdomain/zero/1.0/">Licence</ref>
              </licence>
            </availability>
          </publicationStmt>
        """
        pbsoup = BeautifulSoup(pubstmt_as_string, 'xml')
        pbstmt = pbsoup.publicationStmt
        filedesc.append(pbstmt)
        
    def __add_sourcedesc(self, filedesc):
        sourcedesc_as_string = """
          <sourceDesc>
            <bibl type="digitalSource">
              <name>oenb</name>
              <idno type="URL">ENTER SOURCE URL HERE</idno>
              <availability status="free">
                <p>In the public domain.</p>
              </availability>
            </bibl>
          </sourceDesc>
        """
        sdsoup = BeautifulSoup(sourcedesc_as_string, 'xml')
        sd = sdsoup.sourceDesc
        filedesc.append(sd)
        
        
    def __add_title_to_header(self, header, line):
        titlest = header.find('titleStmt')
        title = Tag(name='title')
        title['type'] = 'main'
        title.append(line[6:].strip())
        titlest.append(title)
        
    def __add_author_to_header(self, header, line):
        fdesc = header.find('titleStmt')
        author = Tag(name='author')
        author.append(line[7:].strip())
        fdesc.append(author)
        
    def __add_subtitle_to_header(self, header, line):
        titlest = header.find('titleStmt')
        title = Tag(name='title')
        title['type'] = 'sub'
        title.append(line[9:].strip())
        titlest.append(title)
        
    ### Main parsing methods:
        
    def __parse_lines(self, ezdramalines):
                    
        self.lasting_comment = False # for multiline comment parsing
        
        for line in ezdramalines:
            if line.startswith('@author'):
                self.__add_author_to_header(self.tree_root.teiHeader, line.strip())
            elif line.startswith('@title'):
                self.__add_title_to_header(self.tree_root.teiHeader, line.strip())
            elif line.startswith('@subtitle'):
                self.__add_subtitle_to_header(self.tree_root.teiHeader, line.strip())
            else:
                first_character = line[:1] # cutting off the first special symbol
                rest_of_line = line[1:] # taking the rest of the line
                if first_character in self.special_symb_list:
                    self.__handle_line_with_markup(first_character, rest_of_line)
                else:
                    if self.lasting_comment and re.search(r'-->\s*$', line):
                        line = re.sub(r'(\<\!--|--\>)', '',line)
                        self.current_lowest_tag.append(line)
                        self.current_lowest_tag = self.current_lowest_div
                        self.lasting_comment = False
                    else:
                        self.current_lowest_tag.append(line)
        
        
    def process_file(self, path_to_file):
        with open(path_to_file) as openfile:
            file_lines = openfile.readlines()
        self.parse_lines_to_xml(file_lines)
        self.output_to_file(path_to_file.replace('.txt', '.xml'))


    def parse_lines_to_xml(self, ezdramalines):
        '''this method takes list of lines 
        containing a whole play 
        in ezdrama format (see sample 
        in the README: https://github.com/dracor-org/ezdrama)'''
        self.__parse_lines(ezdramalines)
        self.__post_process()
        pretty_tree = self.__indent_dracor_style()
        self.tree_to_write = self.__add_spaces_inline_stages(pretty_tree)
        
          
        
    def __handle_line_with_markup(self, first_character, rest_of_line):
        ''' processes a line with specific ezdrama markup symbol at the start
        writes it into current lowest tag or current lowest div
        updates current lowest tag/div'''
        if first_character == '$':
            new_stage = Tag(name='stage')
            new_stage.append(rest_of_line.strip())
            self.current_lowest_div.append(new_stage)
            self.current_lowest_tag = new_stage # if you comment this out, 
            #your $-<stage>s will stop being multiline,
            # they will just capture one $-marked line and all the next lines will go to previous lowest tag
        #elif first_character == '(': DELETE
            # this will only ever work if ( is added to the special symbols list 
            # which is regulated with the bracketstages parameter on init
         #   new_stage = Tag(name='stage')
         #   new_stage.append(first_character) # bracket remains part of stage
         #   new_stage.append(rest_of_line.strip())
         #   self.current_lowest_div.append(new_stage)
        elif first_character == '@':
            new_sp = Tag(name='sp')
            new_sp.append(rest_of_line)
            self.current_lowest_div.append(new_sp)
            self.current_lowest_tag = new_sp
        elif first_character == '^':
            new_cl = Tag(name='castList')
            new_cl.append(rest_of_line)
            self.tree_root.front.append(new_cl)
            self.current_lowest_tag = new_cl
        elif first_character == '<':
            #handle_comment(first_chara) REWRITE AS DEDICATED METHOD/FUNCTION
            if rest_of_line.startswith('!--'):
                new_comment = Tag(name='comment')
                self.current_lowest_div.append(new_comment)
                if not re.search(r'-->\s*$', rest_of_line):
                    self.lasting_comment=True
                    self.current_lowest_tag = new_comment
                new_comment.append(re.sub(r'(\<?\!--|--\>)', '', rest_of_line))
            else:
                self.current_lowest_tag.append(rest_of_line)


        elif first_character == '#':
            new_div = Tag(name='div')
            head = Tag(name='head')
            head.append(rest_of_line.strip('#'))
            new_div_level = self.__get_div_level(rest_of_line)
            new_div['level'] = new_div_level
            new_div.append(head)

            current_level = int(self.current_lowest_div.attrs.get('level', 0))

            if new_div_level > current_level:
                self.current_lowest_div.append(new_div)
            elif new_div_level == current_level:
                self.current_lowest_div.parent.append(new_div)
            else:
                # Traverse upwards until a div with lower level is found
                temp_div = self.current_lowest_div
                while temp_div and int(temp_div.attrs.get('level', 0)) >= new_div_level:
                    temp_div = temp_div.parent
                if temp_div:
                    temp_div.append(new_div)

            self.current_lowest_div = new_div
            self.current_lowest_tag = new_div

    
    
    ## Aux technical processing functions
        
    def __add_spaces_inline_stages(self, tree_as_string):
        '''some technical fix which was at some point 
        asked for by the draCor maintainter AFAIR''' 

        tree_as_string = re.sub(r'</stage>([^\s<>])', r'</stage> \1', tree_as_string)
        tree_as_string = re.sub(r'([^\s<>])<stage>', r'\1 <stage>', tree_as_string)
        return tree_as_string
    
    def __get_div_level(self, line):
        div_level = 1 # since we already located one # and since 0 is <body> level in this model
        for char in line:
            if char == '#':
                div_level+=1
            else:
                break
        return div_level
                

    ### Post-processing functions 
    
    def __post_process(self):
        set_of_char_pairs = set() # set of ID + charname pairs for particDesc
        
        self.__add_cast_items()
        
        del self.tree_root.find('body')['level']
        
        for sp in self.tree_root.find_all('sp'):
            self.__post_process_sp(sp)
            if 'who' in sp.attrs:
                set_of_char_pairs.add((sp['who'], sp.speaker.text.strip('.,:!; '))) 
        for div in self.tree_root.find_all('div'):
            level = int(div.attrs.get('level', -1))
            div.attrs = {}  # löscht "level" und mögliche Reste

            if level == 1:
                div['type'] = 'act'
            elif level == 2:
                div['type'] = 'scene'
            elif level == 3:
                div['type'] = 'subscene'

        self.__add_particdesc_to_header(set_of_char_pairs)
        self.__add_rev_desc()    
        
    
    def __add_cast_items(self):
        castList = self.tree_root.find('castList')
        if castList:
            casttext = castList.text
            cast_lines = casttext.split('\n')
            castList.clear()
            # first line is head
            castHead = Tag(name='head')
            castHead.append(cast_lines[0])
            castList.append(castHead)
            # next lines -- castItems
            for line in cast_lines[1:]:
                castItem = Tag(name='castItem')
                castItem.append(line)
                castList.append(castItem)
    
    
    def __add_rev_desc(self):
        revdesc_as_string = f"""
        <revisionDesc>
             <listChange>
            <change when="{datetime.today().strftime('%Y-%m-%d')}">DESCRIBE CHANGE</change>
            </listChange>
        </revisionDesc>"""
        rdsoup = BeautifulSoup(revdesc_as_string, 'xml')
        rd = rdsoup.revisionDesc
        self.tree_root.teiHeader.append(rd)
        
        
    def __add_particdesc_to_header(self, set_of_char_pairs):
        #print(set_of_char_pairs)
        profileDesc = Tag(name = 'profileDesc')
        particDesc = Tag(name = 'particDesc')
        profileDesc.append(particDesc)
        listPerson = Tag(name = 'listPerson')
        particDesc.append(listPerson)
        for pair in set_of_char_pairs:
            person = Tag(name = 'person')
            person['xml:id'] = pair[0].strip('#')
            person['sex'] = self.__guess_gender(person['xml:id'])
            persName = Tag(name = 'persName')
            person.append(persName)
            #print(pair[1])
            persName.append(pair[1])
            listPerson.append(person)
        teiHeader = self.tree_root.teiHeader
        teiHeader.append(profileDesc)
        
    
    def __handle_speaker_in_sp(self, sp, first_line):
        speaker = Tag(name='speaker')
        sp.append(speaker)
        check_stage = re.search(r'([^()]+)(\(.+?\))([.,:!;])?', first_line)
        if check_stage and self.bracketstages:
            speaker.append(check_stage.group(1).strip())
            inside_stage = Tag(name='stage')
            inside_stage.append(check_stage.group(2).strip())
            sp.append(inside_stage)

            ending_punct = check_stage.group(3)
            if ending_punct is not None:
                speaker.append(ending_punct.strip())
        else:
            speaker.append(first_line.strip())
            
        self.__transliterate_speaker_ids(sp, speaker)
        
        
            
    def __transliterate_speaker_ids(self, sp, speaker):
        
        ## ukrainian ids transliterated
        if re.search(r'[йцукенгшщзхъфывапролджэячсмитью]', speaker.text.lower()):
            clean_who = self.__clean_after_translit(translit(speaker.text.strip('. '), 'uk', 
                                                      reversed=True)).lower()
            clean_who = clean_who.strip('.,:!; ')

        ## yiddish ids transliterated
        elif re.search('[אאַאָבבֿגדהוװוּױזחטייִײײַככּךלמםנןסעפּפֿףצץקרששׂתּת]', speaker.text.lower()):
            clean_who = yiddish.transliterate(speaker.text.strip('.,:!; '))
            clean_who = re.sub(r'[\u0591-\u05BD\u05C1\u05C2\\u05C7]', ' ', clean_who)
        else:
            clean_who = speaker.text.strip('.,:!; ').lower()
            clean_who = self.__clean_after_translit(clean_who)
            
            
        clean_who = self.__fix_starting_w_number(clean_who)
        
        sp['who'] = f'#{clean_who}'
        
        
    def __fix_starting_w_number(self, clean_who): ##  1-ja_divchyna etc.
        match = re.match(r'(\d+.*?)(_)(.+)', clean_who)
        if match is not None:
            clean_who = f'{match.group(3)}{match.group(2)}{match.group(1)}'
        return clean_who
        
    def __clean_after_translit(self, line):
        line = line.replace('і', 'i')
        line = line.replace('ї', 'i')
        line = line.replace('і', 'i')
        line = line.replace('є', 'e')
        line = line.replace('є', 'e')
        line = line.replace('ы', 'y')
        line = line.replace("'", "")
        line = line.replace("’", "")
        line = line.replace("«", "")
        line = line.replace("»", "")
        line = line.replace("′", "")
        line = line.replace(" ", "_")
        return line
        
        
    def __handle_line_with_brackets(self, speechtext, check_inline_brackets):        
        for triplet in check_inline_brackets:
            if len(triplet[0]) > 0:
                speechtext.append(triplet[0])
            inside_stage = Tag(name='stage')
            inside_stage['type'] = 'inline'
            inside_stage.append(triplet[1].strip())
            speechtext.append(inside_stage)
            if len(triplet[2]) > 0:
                speechtext.append(triplet[2])

        
    def __guess_gender(self, someid):
        female_suffixes = ('a', 'e', 'ine', 'ene', 'ette', 'ett', 'elle', 'ia', 'ie', 'ea', 'traud', 'gard', 'ique', 'ise')
        lowered = someid.lower()
        if 'frau' in lowered:
            return 'FEMALE'
        if lowered.endswith(female_suffixes):
            return 'FEMALE'
        return 'MALE'

        
    def __add_line_to_speech(self, line, sp, line_is_prose):
        if line_is_prose:
            speechtext = Tag(name='p')
        else:
            speechtext = Tag(name='l')
        if len(line) > 0:
            check_inline_brackets  = re.findall(r'([^()]*)(\(.+?\)[.,:!;]?)([^()]*)', line)
            if check_inline_brackets and self.bracketstages:
                self.__handle_line_with_brackets(speechtext, check_inline_brackets)
            else:
                speechtext.append(line)
            sp.append(speechtext)
            
            
    def __handle_speech_in_sp(self, sp, text_split_in_lines):
        current_speech_is_prose = self.is_prose # memorising the global prose or verse mode
        for line in text_split_in_lines[1:]:
            if line.startswith('%'):
                inlinestage = Tag(name='stage')
                inlinestage.append(line.strip('%'))
                sp.append(inlinestage)
            elif line.startswith('~'): # switch from main mode (prose or verse) to the opposite
                current_speech_is_prose = not current_speech_is_prose 
                line = line.strip('~') # removing the special switch symbol
                self.__add_line_to_speech(line, sp, current_speech_is_prose)
            else:
                self.__add_line_to_speech(line, sp, current_speech_is_prose)
        
        
    def __post_process_sp(self, sp):
        text_of_sp = sp.text
        sp.clear()
        text_split_in_lines = text_of_sp.split('\n')
        first_line = text_split_in_lines[0]
        
        # handle speaker line
        self.__handle_speaker_in_sp(sp, first_line)
        
        # handle the rest of the sp
        self.__handle_speech_in_sp(sp, text_split_in_lines)
        
        
        
    ## Data output methods
        
    def __indent_dracor_style(self):
        
        output = self.tree_root.prettify()
        
        output = re.sub(r'(<[^/]+?>)\n\s+([^<>\s])', '\\1\\2', output) ## removing linebreak after the opening tag
        output = re.sub(r'([^<>\s])\n\s+(</.+?>)', '\\1\\2', output) ## removing linebreak before the closing tag
        
        ## fixing excessive indentation in speakers and stages
        
        output = re.sub(r'(<speaker>)([^<>]+)\s*\n\s*([^<>]+)(</speaker>)', '\\1\\2\\3\\4', output)
        
        ## inline stage dedent
        output = re.sub(r'([\n\s]+)(<stage type="inline">)([^<>]+)(</stage>)([\n\s]+)',
                        '<stage>\\3\\4', output)
        
        
        
        ## duplicating indents dracor-style (prettify gives 1 indent)
        output_lines = []  
        for line in output.split('\n'):
            newline = re.sub('^( +)', '\\1'*2, line) 
            output_lines.append(newline) 
            
        output = '\n'.join(output_lines)
        
        ## checking if it's still valid xml after all the indentation work
        BeautifulSoup(output, 'xml') 
            
        #returning
        return output
    
        
    def output_to_file(self, newfilepath):
        with open(newfilepath, 'w') as outfile:
            outfile.write(self.tree_to_write)
            self.outputname = newfilepath


if __name__ == "__main__":
    parser = Parser()
    parser.process_file('gesamttext_clean.txt')
