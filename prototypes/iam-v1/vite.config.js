import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({plugins:[vue()],server:{host:'127.0.0.1',port:5197,strictPort:true,allowedHosts:['iam-prototype.localhost']},preview:{host:'127.0.0.1',port:5197,strictPort:true}})
