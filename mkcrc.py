import zipfile
import sys

def calculate_checksums(pk3):
    z = zipfile.ZipFile(pk3, "r")

    table = b""
    count = 0
    for info in z.infolist():
        if not info.CRC:
            continue

        table += (info.CRC & 0xFFFFFFFF).to_bytes(4, "little", signed=False)
        count += 1
    
    a = 0
    output = f'"{pk3}",\n(\n    {count},\n    b"'
    for i in table:
        if a > 0 and a % 16 == 0:
            output += '"\\\n    b"'
        output += '\\x{:02x}'.format(i)
        a += 1

    output += '"\n)'
    print(output)

if __name__ == '__main__':
    calculate_checksums(sys.argv[1]) 