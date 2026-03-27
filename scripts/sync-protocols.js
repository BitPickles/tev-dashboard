#!/usr/bin/env node

// 同步 all-protocols.json
console.log('=== 同步 all-protocols.json ===');
console.log('从 data/ 目录收集所有协议数据...');

const fs = require('fs');
const path = require('path');

// 读取所有协议数据文件
const protocols = {};
const protocolFiles = fs.readdirSync('./data').filter(file => file.endsWith('.json'));

protocolFiles.forEach(file => {
    const protocolName = file.replace('.json', '');
    const data = JSON.parse(fs.readFileSync(path.join('./data', file), 'utf8'));
    protocols[protocolName] = data;
});

// 保存汇总数据
fs.writeFileSync('./all-protocols.json', JSON.stringify(protocols, null, 2));

console.log('✅ 已收集 ' + protocolFiles.length + ' 个协议数据');
console.log('✅ 已更新 all-protocols.json');
console.log('📋 协议同步完成\n');