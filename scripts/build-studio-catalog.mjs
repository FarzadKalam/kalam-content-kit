import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
import {ROOT,writeJson} from './lib/paths.mjs';
import {python} from './lib/studio-runtime.mjs';
const base=path.join(ROOT,'vendor/studio/source/kalam-design-studio/apps/admin-miniapp/src');
const files=fs.readdirSync(base).filter(f=>/\.tsx?$/.test(f)).sort();
const catalog={schemaVersion:1,templates:[],initialContent:{},constants:[],stateDefaults:[],types:[],controls:[],requestBuilders:[]};
function literal(n,source) {
  if(!n)return null;
  if(ts.isAsExpression(n)||ts.isParenthesizedExpression(n))return literal(n.expression,source);
  if(ts.isStringLiteral(n)||ts.isNoSubstitutionTemplateLiteral(n))return n.text;
  if(ts.isNumericLiteral(n))return Number(n.text);
  if(n.kind===ts.SyntaxKind.TrueKeyword)return true;
  if(n.kind===ts.SyntaxKind.FalseKeyword)return false;
  if(n.kind===ts.SyntaxKind.NullKeyword)return null;
  if(ts.isArrayLiteralExpression(n))return n.elements.map(x=>literal(x,source));
  if(ts.isObjectLiteralExpression(n)&&n.properties.every(ts.isPropertyAssignment))return Object.fromEntries(n.properties.map(p=>[p.name.getText(source).replace(/^['"]|['"]$/g,''),literal(p.initializer,source)]));
  return {expression:n.getText(source)};
}
const sourcePath=n=>n.getSourceFile().fileName.replaceAll('\\','/').split('/').at(-1);
function location(n,s){return {file:sourcePath(n),line:s.getLineAndCharacterOfPosition(n.getStart(s)).line+1};}
function conditions(n,s) {
  const list=[];
  for(let p=n.parent;p;p=p.parent) {
    if(ts.isConditionalExpression(p))list.push(p.condition.getText(s));
    if(ts.isBinaryExpression(p)&&p.operatorToken.kind===ts.SyntaxKind.AmpersandAmpersandToken)list.push(p.left.getText(s));
    if(ts.isIfStatement(p))list.push(p.expression.getText(s));
  }
  return [...new Set(list)].filter(x=>x.length<600);
}
for(const file of files) {
  const source=ts.createSourceFile(file,fs.readFileSync(path.join(base,file),'utf8'),ts.ScriptTarget.Latest,true,file.endsWith('.tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS);
  function visit(node) {
    if(ts.isVariableDeclaration(node)&&node.initializer) {
      if(node.name.getText(source)==='templateDefinitions')catalog.templates=literal(node.initializer,source);
      if(node.name.getText(source)==='initialContent')catalog.initialContent=literal(node.initializer,source);
      let value=node.initializer;
      while(ts.isAsExpression(value)||ts.isParenthesizedExpression(value))value=value.expression;
      if(ts.isIdentifier(node.name)&&(ts.isArrayLiteralExpression(value)||ts.isObjectLiteralExpression(value))&&value.getText(source).length<24000)catalog.constants.push({name:node.name.text,value:literal(value,source),...location(node,source)});
      if(ts.isArrayBindingPattern(node.name)&&ts.isCallExpression(node.initializer)&&node.initializer.expression.getText(source)==='useState') {
        catalog.stateDefaults.push({name:node.name.elements[0].getText(source),type:node.initializer.typeArguments?.map(x=>x.getText(source)).join(',')||null,
          default:literal(node.initializer.arguments[0],source),...location(node,source)});
      }
    }
    if(ts.isTypeAliasDeclaration(node)||ts.isInterfaceDeclaration(node))catalog.types.push({name:node.name.text,source:node.getText(source),...location(node,source)});
    if(ts.isJsxElement(node)||ts.isJsxSelfClosingElement(node)) {
      const opening=ts.isJsxElement(node)?node.openingElement:node;
      const tag=opening.tagName.getText(source);
      if(['input','select','textarea','VisualTextArea','ReferenceAssetPicker','ProjectReferenceGrid','VideoSceneEditor','ModernSwitch'].includes(tag)) {
        const attributes=Object.fromEntries(opening.attributes.properties.filter(ts.isJsxAttribute).map(a=>[a.name.getText(source),a.initializer?.getText(source)||true]));
        const options=ts.isJsxElement(node)?node.children.filter(ts.isJsxElement).filter(c=>c.openingElement.tagName.getText(source)==='option').map(c=>({value:c.openingElement.attributes.properties.find(a=>ts.isJsxAttribute(a)&&a.name.text==='value')?.initializer?.getText(source),label:c.children.map(c=>c.getText(source)).join('')})):[];
        let parent=node.parent;while(parent&&!(ts.isJsxElement(parent)&&parent.openingElement.tagName.getText(source)==='label'))parent=parent.parent;
        const label=parent?.children.filter(ts.isJsxText).map(x=>x.text.trim()).filter(Boolean).join(' ')||attributes['aria-label']||attributes.label||attributes.title||attributes.placeholder||'';
        catalog.controls.push({tag,label,attributes,options,conditions:conditions(node,source),...location(node,source)});
      }
    }
    if(ts.isVariableDeclaration(node)&&ts.isIdentifier(node.name)&&node.initializer&&ts.isObjectLiteralExpression(node.initializer)) {
      const keys=node.initializer.properties.filter(ts.isPropertyAssignment).map(p=>p.name.getText(source));
      if(['payload','videoProject','voiceProject'].includes(node.name.text)||keys.includes('projectId')&&keys.includes('lines'))catalog.requestBuilders.push({name:node.name.text,source:node.initializer.getText(source),...location(node,source)});
    }
    ts.forEachChild(node,visit);
  }
  visit(source);
}
writeJson(path.join(ROOT,'catalog/studio-ui.json'),catalog);
const compiled=JSON.parse(python([path.join(ROOT,'scripts/studio.py'),'catalog']));
writeJson(path.join(ROOT,'catalog/studio.json'),compiled);
writeJson(path.join(ROOT,'catalog/public-data.json'),JSON.parse(python([path.join(ROOT,'scripts/public_data.py'),'catalog'])));
console.log(JSON.stringify({templates:catalog.templates.length,contentFields:Object.keys(catalog.initialContent).length,controls:catalog.controls.length,stateDefaults:catalog.stateDefaults.length,editorialProfiles:Object.keys(compiled.editorialProfiles).length}));
