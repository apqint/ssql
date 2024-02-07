import re
import sys


data_type = {
    "vchar": "varchar",
    "nvchar": "nvarchar",
    "vbinary": "varbinary", 
}
def compile(source, path):
    with open(source, "r") as file:
        codeSource = file.read()
    output=''
    preDatabaseExecution = re.findall("(.+?)\nwith", codeSource, flags=re.S | re.U | re.I)[0]
    line_count = 1
    for line in preDatabaseExecution.splitlines():
        extracted_line = re.findall("(.*?)[\n|^;]", line+'\n', re.S | re.I | re.U | re.M)[0]
        temp = re.findall("(create|checkpoint) ?(.*)", extracted_line, (re.I))
        for action, identificator in temp:
            match action.lower():
                case "create":
                    output+=f"CREATE DATABASE {identificator};\n"
                case "checkpoint":
                    output+=f"START TRANSACTION;"
                case _: 
                    print('Error in line: ', line_count, action, identificator)
        line_count+=1
    output+="\n"
    perDatabaseAction = re.findall("with .*?(.*?){(.*?)\n}", codeSource, re.S | re.I)
    for db, action_ in perDatabaseAction:
        output+=f"\nUSE {db};\n\n"
        for line in action_.splitlines():
            line = line.strip()
            try:
                action, identificator = re.findall(r"(create|add|get|change|shorten|save)\s*(.*\w)", line, re.I | re.M | re.S)[0]
            except IndexError:
                continue
            match action.lower():
                case "create":
                    script = re.findall(r"create\s*" + identificator + r"\s*{(.*?)}", action_, re.I | re.M | re.S)[0]
                    output+="CREATE TABLE " + identificator + " (\n"
                    for script_line in script.splitlines():
                        line_count += 1
                        script_line = script_line.strip()
                        if script_line=="": continue
                        variable_name = script_line.split(' ')[0]
                        script_line = script_line.split(' ', 1)[1].replace(';','')
                        output+=(f'\t{variable_name} ')
                        for keyword in script_line.split(' '):
                            keyword+='\n'
                            keyword = re.findall(r"(\w*)[\(|\n]", keyword, re.I)[0]
                            match keyword.lower():
                                case "defined": output+="NOT NULL "
                                case "primary": output+="PRIMARY KEY "
                                case "unique": output+="UNIQUE "
                                case "default":
                                    default_value = re.findall(r"default\s*\((.+?)\)", script_line, re.I | re.M | re.S)[0]
                                    quotes = "" if default_value.isdigit() or str(float(default_value))==default_value else ("" if "'" in default_value or '"' in default_value else "'")
                                    output+=f"DEFAULT({quotes}{default_value}{quotes}) "
                                case "check":
                                    check_value = re.findall(r"check\s*\((.+?)\)", script_line, re.I | re.M)[0]
                                    output+=f"CHECK({check_value}) "
                                case "foreign":
                                    referenced_table, referenced_column = re.findall(r"foreign\s*\((.+?)->(.+?)\)", script_line, re.M | re.I)[0]
                                    output+=f"FOREIGN KEY REFERENCES {referenced_table}({referenced_column}) "
                                case "smallint" | "mediumint" | "int" | "double" | "float" | "money" | "bool" | "date" | "year" | "longtext" | "longblob" | "mediumtext" | "mediumblob" | "boolean" | "datetime":
                                    output+=f"{keyword.upper()} "
                                case "char" | "vchar" | "nvchar" | "vbinary" | "binary" | "text" | "blob" | "decimal" | "timestamp":
                                    value = re.findall(rf"{keyword.strip().lower()}\s*\((.+?)\)", script_line, re.I | re.M)[0]
                                    true_keyword = data_type.get(keyword.strip().lower(), keyword)
                                    output+=f"{true_keyword.upper()}({value}) "
                        output=output[:-1]+",\n"
                    output=output[:-2]+'\n)\n\n'
                case "add":
                    script = re.findall(r"add\s*" + identificator + r"\s*{(.*?)}", action_, re.I | re.M | re.S)[0]
                    output+=f"INSERT INTO {identificator} VALUES \n"
                    for line in script.splitlines():
                        line = line.strip().replace(';','')
                        if line=='': continue
                        output+="\t("
                        output+=line + '),\n'
                    output=output[:-2]+'\n\n'
                case "get":
                    if "where" in identificator:
                        target_column, target_table, if_condition = re.findall(r"(.*)\s*from\s*(.*)\s*where\s*(.*)", identificator, re.I | re.M)[0]
                        output+=f"SELECT {target_column.strip()} FROM {target_table.strip()} WHERE {if_condition};\n"
                        continue
                    target_column, target_table = re.findall(r"(.*)\s*from\s*(.*)", identificator, re.I | re.M)[0]
                    output+=f"SELECT {target_column.strip()} FROM {target_table};\n"
                case "change":
                    script = re.findall(r"change\s*"+identificator+r"\s*{(.*?)}", action_, re.S | re.I | re.M)[0].strip()
                    output+=f"UPDATE {identificator} SET"
                    for line in script.splitlines():
                        line = line.strip()
                        if line=='': continue
                        if "where" in line.strip().lower():
                            output = output[:-1]
                            condition = re.findall(r"where\s*(.*)", line, re.I)[0].replace('and', 'AND').replace('or', 'OR')
                            output+=" WHERE " + condition
                            continue
                        id_, val_ = re.findall(r"(.*?)\s*=\s*(.*)", line, re.I)[0]
                        output+=f" {id_.strip()} = {val_.strip()},"
                    output+=';\n'
                case "shorten":
                    if "if" in line.lower():
                        target_table, if_condition =  re.findall(r"(.*?)\s*if\s*(.*)", identificator, re.I)[0]
                        output+=f"DELETE FROM {target_table} WHERE {if_condition};\n"
                    else:
                        output+=f"DELETE FROM {identificator};\n"
                case "save":
                    if identificator=="load":
                        output+="ROLLBACK;\n"
                    elif identificator=="commit":
                        output+="COMMIT;\n"
    with open(path, 'w+') as file:
        file.write(output)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: main.py -s <source_value> -o <output_value>")
    else:
        source = sys.argv[2]
        path = sys.argv[4]
        compile(source, path)
