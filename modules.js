
class Park {
    constructor(trails, pois, time) {
        this.trails = trails // array
        this.pois = pois
        this.time = time
    }
}

class Trail {
    constructor(type, coords, time) {
        this.type = type
        this.coords = coords // array
        this.time = time
    }
}

function parseDataFile(file, getParksOnly=false) {
    return fetch(file)
        .then(response => response.text())
        .then(text => {
            response = String(text).split('\n')
            data = []
            i=0
            while (i < response.length) {
                line = String(response[i]).replace(/(\r\n|\n|\r)/gm, "")
                if (line == "") {
                    i++
                    continue
                }
                header = line.split(" ")[0]
                contentIndex = header.length+1
                content = line.substring(contentIndex).split(" - ")
                data.push({header, content})
                i++
            }
            returnData = []
            i=0
            if (getParksOnly) {
                for (obj of data) {
                    if (obj.header == "START") {
                        park = obj.content[0]
                        if (!returnData.includes(park)) {
                            returnData.push(park)
                        }
                    }
                }
            } else {
                while (i < data.length) {
                    switch (data[i].header) {
                        case "START":
                            startData = data[i].content
                            returnData.push({
                                header: "START",
                                park: startData[0],
                                pathType: startData[1],
                                time: startData[2]
                            })
                            i+=2
                            break
                        case "COORDS":
                            time = data[i-1].content[0]
                            coords = data[i].content[0].split(',')
                            coords = [parseFloat(coords[0]), parseFloat(coords[1])]
                            accuracy = parseFloat(data[i+1].content[0])
                            returnData.push({
                                header: "COORDS", time, coords, accuracy})
                            i+=3
                            break
                        case "POI":
                            time = data[i-1].content[0]
                            coords = data[i+1].content[0].split(',')
                            coords = [parseFloat(coords[0]), parseFloat(coords[1])]
                            accuracy = parseFloat(data[i+2].content[0])
                            imgId = data[i+3].content[0]
                            returnData.push({
                                header: "POI", time, coords, accuracy, imgId
                            })
                            i+=5
                            break
                    }
                }
            }

            return new Promise((resolve) => {
                console.log(returnData)
                resolve(returnData)
            })
        });
}