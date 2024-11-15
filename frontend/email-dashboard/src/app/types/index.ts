export interface EmailTemplate {
    id: string;
    name: string;
    content: string;
    subject: string;
    variables: string[];
  }
  
  export interface EmailData {
    id: string;
    recipientEmail: string;
    recipientName: string;
    status: 'pending' | 'sent' | 'failed' | 'scheduled';
    deliveryStatus: 'delivered' | 'bounced' | 'opened' | null;
    scheduledTime?: Date;
    sentTime?: Date;
    templateId: string;
    customData: Record<string, any>;
  }
  
  // In prisma/schema.prisma
  generator client {
    provider = "prisma-client-js"
  }
  
  datasource db {
    provider = "postgresql"
    url      = env("DATABASE_URL")
  }
  
  model EmailTemplate {
    id        String   @id @default(cuid())
    name      String
    content   String
    subject   String
    variables String[]
    createdAt DateTime @default(now())
    updatedAt DateTime @updatedAt
    emails    Email[]
  }
  
  model Email {
    id             String    @id @default(cuid())
    recipientEmail String
    recipientName  String?
    status         String    @default("pending")
    deliveryStatus String?
    scheduledTime  DateTime?
    sentTime       DateTime?
    templateId     String
    template       EmailTemplate @relation(fields: [templateId], references: [id])
    customData     Json?
    createdAt      DateTime  @default(now())
    updatedAt      DateTime  @updatedAt
  }