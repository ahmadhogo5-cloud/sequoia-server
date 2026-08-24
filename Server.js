const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");
const dns = require("dns").promises;
const net = require("net");

const PORT = process.env.PORT || 3000;

const MAX_SOURCE_BYTES =
    Number(process.env.MAX_SOURCE_BYTES) ||
    25 * 1024 * 1024;

// النطاقات التي تسمح للسيرفر بقراءتها
const ALLOWED_HOSTS = (process.env.ALLOWED_HOSTS || "")
    .split(",")
    .map(host => host.trim().toLowerCase())
    .filter(Boolean);


// ===============================
// إرسال JSON
// ===============================

function sendJSON(res, statusCode, data) {

    res.writeHead(statusCode, {
        "Content-Type": "application/json; charset=utf-8"
    });

    res.end(JSON.stringify(data));
}


// ===============================
// فحص هل الـ IP داخلي
// ===============================

function isPrivateIP(ip) {

    if (!net.isIP(ip)) {
        return false;
    }

    if (ip === "127.0.0.1" || ip === "::1") {
        return true;
    }

    if (ip.startsWith("10.")) {
        return true;
    }

    if (ip.startsWith("192.168.")) {
        return true;
    }

    if (ip.startsWith("169.254.")) {
        return true;
    }

    const parts = ip.split(".");

    if (
        parts.length === 4 &&
        parts[0] === "172"
    ) {

        const second = Number(parts[1]);

        if (second >= 16 && second <= 31) {
            return true;
        }
    }

    if (
        ip.startsWith("fc") ||
        ip.startsWith("fd") ||
        ip.startsWith("fe80:")
    ) {
        return true;
    }

    return false;
}


// ===============================
// فحص النطاق
// ===============================

async function validateURL(inputURL) {

    let url;

    try {

        url = new URL(inputURL);

    } catch {

        throw new Error("الرابط غير صالح");
    }


    if (
        url.protocol !== "http:" &&
        url.protocol !== "https:"
    ) {

        throw new Error(
            "يُسمح فقط بروابط HTTP و HTTPS"
        );
    }


    const hostname =
        url.hostname.toLowerCase();


    if (
        hostname === "localhost" ||
        hostname.endsWith(".local")
    ) {

        throw new Error(
            "هذا النطاق غير مسموح"
        );
    }


    // يجب تحديد ALLOWED_HOSTS في Render
    if (ALLOWED_HOSTS.length === 0) {

        throw new Error(
            "لم يتم إعداد ALLOWED_HOSTS على السيرفر"
        );
    }


    const allowed =
        ALLOWED_HOSTS.some(host =>

            hostname === host ||
            hostname.endsWith("." + host)

        );


    if (!allowed) {

        throw new Error(
            "هذا النطاق غير موجود ضمن ALLOWED_HOSTS"
        );
    }


    // فحص عنوان IP الحقيقي للنطاق
    const addresses =
        await dns.lookup(
            hostname,
            {
                all: true
            }
        );


    if (!addresses.length) {

        throw new Error(
            "تعذر الوصول إلى النطاق"
        );
    }


    for (const item of addresses) {

        if (isPrivateIP(item.address)) {

            throw new Error(
                "عنوان الشبكة الداخلي غير مسموح"
            );
        }
    }


    return url;
}


// ===============================
// جلب محتوى الرابط
// ===============================

async function fetchURL(
    inputURL,
    redirectCount = 0
) {

    if (redirectCount > 5) {

        throw new Error(
            "عدد عمليات إعادة التوجيه كبير جدًا"
        );
    }


    const url =
        await validateURL(inputURL);


    const client =
        url.protocol === "https:"
        ? https
        : http;


    return new Promise(
        (resolve, reject) => {

            const request =
                client.get(
                    url,
                    {
                        headers: {

                            "User-Agent":
                                "Mozilla/5.0 ID-Extractor/1.0",

                            "Accept":
                                "text/html,text/plain,application/json,*/*"
                        }
                    },

                    response => {


                        // Redirect
                        if (
                            response.statusCode >= 300 &&
                            response.statusCode < 400 &&
                            response.headers.location
                        ) {

                            response.resume();

                            const nextURL =
                                new URL(
                                    response.headers.location,
                                    url
                                ).href;


                            fetchURL(
                                nextURL,
                                redirectCount + 1
                            )
                            .then(resolve)
                            .catch(reject);

                            return;
                        }


                        if (
                            response.statusCode < 200 ||
                            response.statusCode >= 300
                        ) {

                            response.resume();

                            reject(
                                new Error(
                                    "المصدر أعاد HTTP " +
                                    response.statusCode
                                )
                            );

                            return;
                        }


                        let totalBytes = 0;

                        const chunks = [];


                        response.on(
                            "data",
                            chunk => {

                                totalBytes +=
                                    chunk.length;


                                if (
                                    totalBytes >
                                    MAX_SOURCE_BYTES
                                ) {

                                    request.destroy();

                                    reject(
                                        new Error(
                                            "حجم المصدر أكبر من الحد المسموح"
                                        )
                                    );

                                    return;
                                }


                                chunks.push(chunk);
                            }
                        );


                        response.on(
                            "end",
                            () => {

                                const body =
                                    Buffer.concat(chunks)
                                    .toString("utf8");


                                resolve(body);
                            }
                        );


                        response.on(
                            "error",
                            reject
                        );
                    }
                );


            request.setTimeout(
                20000,
                () => {

                    request.destroy();

                    reject(
                        new Error(
                            "انتهت مهلة الاتصال"
                        )
                    );
                }
            );


            request.on(
                "error",
                reject
            );
        }
    );
}


// ===============================
// استخراج قيم id=
// ===============================

function extractIDs(text) {

    const regex =
        /(?:[?&\/]|\b)id=([A-Za-z0-9_-]+)/gi;


    const seen =
        new Set();


    const ids = [];


    let match;


    while (
        (match = regex.exec(text))
        !== null
    ) {

        const id =
            match[1];


        if (!seen.has(id)) {

            seen.add(id);

            ids.push(id);
        }
    }


    return ids;
}


// ===============================
// قراءة جسم POST
// ===============================

function readBody(req) {

    return new Promise(
        (resolve, reject) => {

            let body = "";

            let size = 0;


            req.on(
                "data",
                chunk => {

                    size += chunk.length;


                    if (size > 1024 * 1024) {

                        reject(
                            new Error(
                                "حجم الطلب كبير جدًا"
                            )
                        );

                        req.destroy();

                        return;
                    }


                    body +=
                        chunk.toString();
                }
            );


            req.on(
                "end",
                () => {

                    resolve(body);
                }
            );


            req.on(
                "error",
                reject
            );
        }
    );
}


// ===============================
// السيرفر
// ===============================

const server =
    http.createServer(
        async (req, res) => {


            // الصفحة الرئيسية
            if (
                req.method === "GET" &&
                req.url === "/"
            ) {

                const filePath =
                    path.join(
                        __dirname,
                        "public",
                        "index.html"
                    );


                fs.readFile(
                    filePath,
                    (error, data) => {

                        if (error) {

                            res.writeHead(
                                500,
                                {
                                    "Content-Type":
                                    "text/plain; charset=utf-8"
                                }
                            );

                            res.end(
                                "تعذر قراءة index.html"
                            );

                            return;
                        }


                        res.writeHead(
                            200,
                            {
                                "Content-Type":
                                "text/html; charset=utf-8"
                            }
                        );


                        res.end(data);
                    }
                );


                return;
            }


            // API استخراج ID
            if (
                req.method === "POST" &&
                req.url === "/api/extract"
            ) {

                try {

                    const rawBody =
                        await readBody(req);


                    let data;


                    try {

                        data =
                            JSON.parse(rawBody);

                    } catch {

                        throw new Error(
                            "بيانات JSON غير صحيحة"
                        );
                    }


                    if (!data.url) {

                        throw new Error(
                            "لم يتم إرسال رابط"
                        );
                    }


                    const source =
                        await fetchURL(
                            data.url
                        );


                    const ids =
                        extractIDs(source);


                    sendJSON(
                        res,
                        200,
                        {
                            success: true,

                            count:
                                ids.length,

                            ids:
                                ids
                        }
                    );


                } catch (error) {


                    sendJSON(
                        res,
                        400,
                        {
                            success: false,

                            error:
                                error.message
                        }
                    );
                }


                return;
            }


            sendJSON(
                res,
                404,
                {
                    success: false,
                    error: "المسار غير موجود"
                }
            );
        }
    );


// ===============================
// تشغيل السيرفر
// ===============================

server.listen(
    PORT,
    "0.0.0.0",
    () => {

        console.log(
            "Server running on port " +
            PORT
        );

        console.log(
            "Allowed hosts:",
            ALLOWED_HOSTS
        );
    }
);
