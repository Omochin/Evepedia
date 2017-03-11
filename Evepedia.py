import os
import sys
import shutil
import codecs
import yaml
import json
import collections
import sqlalchemy
import sqlalchemy.ext.declarative

LCID = collections.OrderedDict(
    en='English',
    ja='Japanese',
    ru='Russian',
    de='German',
    fr='French',
    zh='Chinese'
)

Base = sqlalchemy.ext.declarative.declarative_base()
class Category(Base):
    __tablename__ = 'categories'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String)


class Group(Base):
    __tablename__ = 'groups'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    categoryID = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('categories.id'))
    name = sqlalchemy.Column(sqlalchemy.String)

    category = sqlalchemy.orm.relationship('Category', backref=sqlalchemy.orm.backref('groups', order_by=id))


class Type(Base):
    __tablename__ = 'types'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)    
    groupID = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('groups.id'))
    raceID = sqlalchemy.Column(sqlalchemy.Integer)
    factionID = sqlalchemy.Column(sqlalchemy.Integer)
    name = sqlalchemy.Column(sqlalchemy.String)
    traits = sqlalchemy.Column(sqlalchemy.String)
    description = sqlalchemy.Column(sqlalchemy.String)

    group = sqlalchemy.orm.relationship('Group', backref=sqlalchemy.orm.backref('types', order_by=id))


url = 'sqlite+pysqlite:///eveonline.sqlite'
engine = sqlalchemy.create_engine(url)

Session = sqlalchemy.orm.sessionmaker(bind=engine)
session = Session()


def import_fsd():
    def load_yaml(path):
        print('Load: ' + path)
        with codecs.open(path, 'r', 'utf-8') as f:
            data = yaml.load(f)

        return data
    
    categoryIDs = load_yaml('./sde/categoryIDs.yaml')    
    groupIDs = load_yaml('./sde/groupIDs.yaml')
    typeIDs = load_yaml('./sde/typeIDs.yaml')    
        
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)        
    
    def id(key):
        try: v = items[key]
        except KeyError: v = ''
        return v

    def dumps(key):
        try: v = items[key]
        except KeyError: v = ''
        return json.dumps(v)

    for i, items in categoryIDs.items():        
        session.add(Category(id=i, name=dumps('name')))
        
    for i, items in groupIDs.items():
        session.add(Group(id=i, categoryID=id('categoryID'), name=dumps('name')))

    for i, items in typeIDs.items():    
        session.add(Type(
            id = i,
            groupID = id('groupID'),            
            raceID = id('raceID'),
            factionID = id('factionID'),
            name = dumps('name'),
            traits = dumps('traits'),
            description = dumps('description')
        ))

    session.commit()


def json2locale(text):
    dict = collections.OrderedDict()
    json_dict = json.loads(text)
    
    for id in LCID.keys():
        try:
            dict[id] = json_dict[id]
        except KeyError:
            dict[id] = json_dict['en']
        except:
            dict[id] = ''

    return dict


def write_html(name, title, body):
    html = '<!DOCTYPE html><html><head><title>' + title + '</title><meta charset="UTF-8"><link rel="stylesheet" type="text/css" href="./evepedia.css"></head><body>'
    html += body
    html += '</body></html>'

    with open('./docs/' + name + '.html', 'w', encoding='utf-8') as f:
        f.write(html)


def locales_table(path, row):
    html = '<table><tr>'
    for locale_name in LCID.values():
        html += '<th>' + locale_name + '</th>'
    html += '</tr>'

    for dict in row:
        html += '<tr>'

        columns = list(dict.values())
        name = columns.pop(0)
        html += '<td><a href="' + path + name + '.html">' + name + '</a></td>'

        for column in columns:
            html += '<td>' + column + '</td>'

        html += '</tr>'

    html += '</table>'
    return html


def read_type(name, type):
    print(name)
    html = '<table><tr><th></th><th>Name</th><th>Description</th></tr>'
    names = json2locale(type.name)
    descriptions = json2locale(type.description)
    for id, lc_name in LCID.items():
        html += '<tr><td>' + lc_name + '</td>'
        html += '<td>' + names[id] + '</td>'
        html += '<td>' + descriptions[id] + '</td></tr>'
    html += '</table>'

    write_html('type/' + name, name, html)


def read_group(name, group):
    row = []
    for type in group.types:
        locale = json2locale(type.name)
        row.append(locale)

        read_type(locale['en'], type)

    write_html('group/' + name, name, locales_table('../type/', row))


def read_category(name, category):
    row = []
    for group in category.groups:
        locale = json2locale(group.name)
        row.append(locale)

        read_group(locale['en'], group)

    write_html('category/' + name, name, locales_table('../group/', row))



if len(sys.argv) > 1:
    if sys.argv[1] == '--import':
        import_fsd()
else:
    for path in ['./docs/', './docs/category/', './docs/group/', './docs/type/']:
        if not os.path.isdir(path):
            os.mkdir(path)

        shutil.copy('./evepedia.css',  path + 'evepedia.css')

    row = []
    for category_id in [6, 7, 8, 16, 20, 32]:    
        category = session.query(Category).filter_by(id=category_id).one()
        locale = json2locale(category.name)
        row.append(locale)

        read_category(locale['en'], category)

    write_html('index', 'Evepedia', locales_table('./category/', row))
