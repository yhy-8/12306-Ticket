def logrecord(filename,data,switch):
    if switch:
        with open(f'log/{str(filename)}.txt', 'w') as file:
            file.write(str(data))
    else:
        return 0