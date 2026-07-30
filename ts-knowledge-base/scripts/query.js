const fs = require('fs');
const https = require('https');

function post(host, path, body, headers) {
    return new Promise((resolve, reject) => {
        const options = { hostname: host, path: path, method: 'POST',
            headers: Object.assign({'Content-Type':'application/json','Accept':'application/json, text/event-stream'}, headers||{}) };
        const req = https.request(options, res => {
            let raw = '';
            res.on('data', chunk => { raw += chunk.toString(); });
            res.on('end', () => resolve(raw));
        });
        req.on('error', reject);
        req.write(JSON.stringify(body));
        req.end();
    });
}

async function query(question, isDeepSearch, userId) {
    const raw = await post('api-ai.h3c.com', '/deepsearch/api-search/v1/streamv1', {
        task: question,
        source: 'www,pmo,cjg,cmp,press,wwwen,ts_sqcs_knowleged',
        user_id: userId || 'z62875',
        session_id: require('crypto').randomUUID(),
        application: 'zhidao',
        searchonly: false,
        outline: false
    }, {});
    
    const lines = raw.split('\n').filter(l => l.startsWith('data: '));
    let finalAnswer = '';
    let references = [];
    
    for (const line of lines) {
        try {
            const obj = JSON.parse(line.substring(6));
            if (obj.code !== 200) continue;
            const meta = obj.data && obj.data.metadata;
            if (!meta) continue;
            const title = meta.title || '';
            const content = obj.data.content || '';
            
            if (title === 'Final Answer' || title === 'Outline Answer') {
                finalAnswer += content;
            }
            if (title === 'Reference information' && obj.data.content_type === 'list') {
                try { references = JSON.parse(content); } catch(e) {}
            }
        } catch(e) {}
    }
    
    return { answer: finalAnswer, references: references };
}

async function main() {
    const question = process.argv[2] || 'R4900 G7 服务器参数';
    const isDeep = process.argv.includes('--deep');
    const userId = 'z62875';
    
    console.log('问题: ' + question);
    console.log('深度思考: ' + isDeep);
    console.log('---------------');
    
    const result = await query(question, isDeep, userId);
    console.log(result.answer);
    
    if (result.references.length > 0) {
        console.log('\n--- 参考资料 ---');
        for (const ref of result.references.slice(0, 5)) {
            console.log('- ' + (ref.title || ref.name || ''));
            console.log('  ' + (ref.original_file_path || ref.url || ''));
        }
    }
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });