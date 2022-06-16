
trailTypeProperties = {
    "Paved": {
        color: "#474245",
        weight: 8
    },
    "Gravel": {
        color: "#ADA197",
        weight: 7
    },
    "Dirt": {
        color: "#6D4830",
        weight: 6
    },
    "Off Trail": {
        color: "#A8896D",
        weight: 4
    },
    "Brush": {
        color: "#00B200",
        weight: 4
    },
    "Deer Path": {
        color: "#2A662A",
        weight: 3
    },
    "_other": {
        color: "#000000",
        weight: 4
    }
}

class Park {
    constructor() {
        this.trailCollection = {}
        this.pois = []
    }

    addTrail(trail, trailType) {
        if (!(trailType in this.trailCollection)) {
            this.trailCollection[trailType] = []
        }
        this.trailCollection[trailType].push(trail)
    }

    getTrails(trailType=null) {
        if (trailType===null) return this.trailCollection
        return this.trailCollection[trailType]
    }

    addPoi(poi) {
        this.pois.push(poi)
    }

    getPois() {
        return this.pois
    }
}

class Trail {
    constructor(coords) {
        this.coords = coords // array
    }
}

async function parseDataFile(file, getParksOnly=false) {
    return fetch(file)
        .then(response => response.text())
        .then(text => {
            response = String(text).split('\n')
            data = []
            i=0
            while (i < response.length) {
                line = String(response[i]).replace(/(\r\n|\n|\r)/gm, "")
                if (line != "") {
                    header = line.split(" ")[0]
                    contentIndex = header.length+1
                    content = line.substring(contentIndex).split(" - ")
                    data.push({header, content})
                }
                i++
            }
            
            returnData = []
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
                i=0
                while (i < data.length) {
                    switch (data[i].header) {
                        case "START":
                            startData = data[i].content
                            returnData.push({
                                header: "START",
                                park: startData[0],
                                trailType: startData[1],
                                time: startData[2]
                            })
                            i+=1
                            break
                        case "TIME":
                            if (data[i+1].header === "COORDS") {
                                coords = data[i+1].content[0].split(',')
                                coords = [parseFloat(coords[0]), parseFloat(coords[1])]
                                returnData.push({
                                    header: "COORDS",
                                    time: data[i].content[0],
                                    coords,
                                    accuracy: parseFloat(data[i+2].content[0])
                                })
                                i+=3
                            }
                            else if (data[i+1].header === "POI") {
                                coords = data[i+2].content[0].split(',')
                                coords = [parseFloat(coords[0]), parseFloat(coords[1])]
                                returnData.push({
                                    header: "POI",
                                    park: data[i+1].content[0],
                                    description: data[i+1].content[1],
                                    time: data[i].content[0],
                                    coords,
                                    accuracy: parseFloat(data[i+3].content[0]),
                                    imgId: data[i+3].content[0],
                                })
                                i+=5
                            }
                            else {
                                throw "error while parsing park data file"
                            }
                            break
                        default:
                            throw "error while parsing park data file"
                    }
                }
            }

            return new Promise((resolve) => {
                // console.log(returnData)
                resolve(returnData)
            })
        });
}